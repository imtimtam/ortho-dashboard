"""
Ortho Performance - claims layer (derived from appointments)
-------------------------------------------------------------
Reads completed appointments from Postgres and writes three objects:

    claims        one row per billed visit        (the outbound bill, "837")
    remittances   one row per ADJUDICATED claim   (the payer's response, "835")
    claim_facts   view joining the two + appointment fields, for Power BI

generate_data.py is not touched. Appointments already carry the seasonality,
growth, location and provider effects, so claims inherit them automatically.

Usage:
    python generate_claims.py

Re-run order if appointments change: generate_data -> ETL -> this script.

Modelling choices (kept deliberately simple):
- Self-Pay visits are excluded: no payer, so nothing to adjudicate.
- allowed = appointments.revenue (your payer_rev_mult already models contracts),
  capped at the CPT's chargemaster price. It is stored as `expected_allowed` on
  claims (known from the contract) and `allowed` on remittances (payer's answer).
- Outcomes are "as of" the last appointment date, like a real system:
  claims not yet adjudicated have no remittance row, and denials still being
  reworked have NULL outcome fields and a NULL resolved_date.
- One remittance per claim holds the FINAL outcome plus a `denied` flag
  (real life has a second remittance after a resubmission).
"""

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.types import Boolean, Date, Numeric, String

from db.session import engine

# ---------------------------------------------------------------------------
# Config - tune these, nothing else needs to change
# ---------------------------------------------------------------------------
SEED = 7                              # separate from generate_data's seed(42)
APPOINTMENTS_TABLE = "appointments"   # point at your CLEANED appointments table

# CPT + chargemaster price per appointment type. Charges sit above any allowed
# amount the generator can produce (max allowed per type is ~234/926/497/251/170).
# Simplifications: Post-Op Check is billed as 99213 (real global-period visits
# use 99024 at $0); PT is billed as one 97110 unit.
CPT_BY_TYPE = {
    "New Patient Consult": ("99204", 650.00),
    "Follow-up":           ("99214", 300.00),
    "Post-Op Check":       ("99213", 225.00),
    "Physical Therapy":    ("97110", 325.00),
    "Injection/Procedure": ("20610", 1200.00),
}

# Per payer: base denial rate, days from submit to payer response (mean, sd),
# and the patient's share of the allowed amount (coinsurance / copay).
PAYER_PARAMS = {
    "PY1": dict(name="Medicare",     deny=0.05, lag=(16, 4), share=0.20),
    "PY2": dict(name="Medi-Cal",     deny=0.10, lag=(38, 8), share=0.00),
    "PY3": dict(name="Blue Cross",   deny=0.07, lag=(27, 6), share=0.15),
    "PY4": dict(name="Aetna",        deny=0.08, lag=(29, 6), share=0.15),
    "PY5": dict(name="Humana",       deny=0.09, lag=(31, 6), share=0.12),
    "PY7": dict(name="UnitedHealth", deny=0.10, lag=(33, 7), share=0.15),
}  # PY6 (Self-Pay) intentionally absent

# Denial-rate multipliers: procedures/PT need authorization, post-ops rarely deny.
TYPE_DENY_MULT = {
    "New Patient Consult": 1.0, "Follow-up": 0.8, "Post-Op Check": 0.5,
    "Physical Therapy": 1.3, "Injection/Procedure": 2.0,
}
LOCATION_DENY_MULT = {"L7": 1.35, "L5": 0.80}   # weaker vs. stronger front-desk process
JANUARY_DENY_MULT = 1.30                         # coverage resets / eligibility errors
MAX_DENY_PROB = 0.40

# Denial reasons. Verify codes/wording at x12.org/codes before publishing.
# group: CO = practice's problem (contractual), PR = shifts to the patient.
# recover: chance the denial is fixed and the payer eventually pays.
DENIAL_REASONS = [
    dict(carc="197", desc="Authorization absent",         group="CO", weight=0.26, recover=0.80),
    dict(carc="16",  desc="Claim lacks information",      group="CO", weight=0.22, recover=0.95),
    dict(carc="50",  desc="Not medically necessary",      group="CO", weight=0.14, recover=0.55),
    dict(carc="29",  desc="Timely filing limit expired",  group="CO", weight=0.07, recover=0.05),
    dict(carc="109", desc="Wrong payer / not covered",    group="CO", weight=0.12, recover=0.75),
    dict(carc="27",  desc="Coverage terminated",          group="PR", weight=0.09, recover=0.30),
    dict(carc="96",  desc="Non-covered charge",           group="PR", weight=0.10, recover=0.20),
]
AUTH_BOOST = {"Injection/Procedure": 2.5, "Physical Therapy": 2.0}  # more 197s here

PR_PATIENT_PAYS = 0.40       # unrecovered PR denials the patient pays in full
PATIENT_PAY_RATE = 0.90      # patients who pay their share on paid claims
SUBMIT_LAG_DAYS = (1, 5)     # service date -> claim submitted
REWORK_DAYS = (25, 55)       # extra days until a recovered denial is paid
WRITEOFF_DAYS = (30, 75)     # extra days until an unrecovered denial is closed out

# ---------------------------------------------------------------------------
# Output view (portable SQL: runs on Postgres and SQLite)
# ---------------------------------------------------------------------------
VIEW_SQL = """
CREATE VIEW claim_facts AS
SELECT
    c.claim_id,
    c.appointment_id,
    a."date"                                   AS service_date,
    c.submit_date,
    r.adjudicated_date,
    r.resolved_date,
    c.payer_id,
    a.location_id,
    a.provider_id,
    a.appointment_type,
    c.cpt_code,
    c.billed,
    COALESCE(r.allowed, c.expected_allowed)    AS allowed,
    c.billed - COALESCE(r.allowed, c.expected_allowed) AS contractual_adjustment,
    r.denied,
    r.carc,
    r.carc_description,
    r.carc || ' - ' || r.carc_description      AS carc_label,
    r.group_code,
    r.first_pass_paid,
    r.recovered,
    r.written_off,
    r.payer_paid,
    r.patient_responsibility,
    r.patient_paid,
    CASE WHEN r.claim_id IS NOT NULL THEN 1 ELSE 0 END    AS is_adjudicated,
    CASE WHEN r.resolved_date IS NOT NULL THEN 1 ELSE 0 END AS is_resolved
FROM claims c
JOIN {appts} a ON a.appointment_id = c.appointment_id
LEFT JOIN remittances r ON r.claim_id = c.claim_id
"""


def to_dates(s: pd.Series) -> list:
    """datetime Series -> list of python dates / None (safe for any DB driver)."""
    return [d.date() if pd.notna(d) else None for d in s]


def main() -> None:
    rng = np.random.default_rng(SEED)

    # ---- 1. Read + defensively clean appointments -------------------------
    appts = pd.read_sql(
        f'SELECT appointment_id, "date", payer_id, location_id, appointment_type, '
        f"status, revenue FROM {APPOINTMENTS_TABLE}",
        engine,
    )
    appts["date"] = pd.to_datetime(appts["date"], errors="coerce")
    appts["revenue"] = pd.to_numeric(appts["revenue"], errors="coerce")
    as_of = appts["date"].max()                       # "today" for the dataset

    dupes = int(appts["appointment_id"].duplicated().sum())
    if dupes:
        raise SystemExit(
            f"{APPOINTMENTS_TABLE} has {dupes} duplicate appointment_ids. Point "
            "APPOINTMENTS_TABLE at the cleaned table (after your ETL), otherwise "
            "claim_facts would repeat those claims."
        )
    appts = appts[
        (appts["status"] == "Completed")
        & appts["revenue"].notna() & (appts["revenue"] > 0)
        & appts["payer_id"].isin(PAYER_PARAMS)        # drops Self-Pay
        & appts["date"].notna()
    ].sort_values("appointment_id").reset_index(drop=True)   # stable row order
    n = len(appts)

    payer = appts["payer_id"]
    atype = appts["appointment_type"]
    unknown = set(atype) - set(CPT_BY_TYPE)
    assert not unknown, f"Add CPT mapping for: {unknown}"

    # ---- 2. Claims (what we billed) ---------------------------------------
    billed = atype.map(lambda t: CPT_BY_TYPE[t][1]).astype(float)
    expected_allowed = np.minimum(appts["revenue"], billed).round(2)
    submit_date = appts["date"] + pd.to_timedelta(
        rng.integers(SUBMIT_LAG_DAYS[0], SUBMIT_LAG_DAYS[1] + 1, n), unit="D")

    claims = pd.DataFrame({
        "claim_id": "CL" + appts["appointment_id"].str[1:],
        "appointment_id": appts["appointment_id"],
        "payer_id": payer,
        "cpt_code": atype.map(lambda t: CPT_BY_TYPE[t][0]),
        "billed": billed.round(2),
        "expected_allowed": expected_allowed,
        "submit_date": to_dates(submit_date),
    })

    # ---- 3. Adjudication: when does the payer answer, and is it a denial? --
    lag_mean = payer.map(lambda p: PAYER_PARAMS[p]["lag"][0]).to_numpy()
    lag_sd = payer.map(lambda p: PAYER_PARAMS[p]["lag"][1]).to_numpy()
    lag = np.clip(rng.normal(lag_mean, lag_sd), 7, 60).round().astype(int)
    adjudicated = submit_date + pd.to_timedelta(lag, unit="D")

    p_deny = (
        payer.map(lambda p: PAYER_PARAMS[p]["deny"]).to_numpy()
        * atype.map(TYPE_DENY_MULT).to_numpy()
        * appts["location_id"].map(LOCATION_DENY_MULT).fillna(1.0).to_numpy()
        * np.where(appts["date"].dt.month == 1, JANUARY_DENY_MULT, 1.0)
    )
    denied = rng.random(n) < np.clip(p_deny, 0, MAX_DENY_PROB)

    # Reason per denied claim; weights shift by appointment type (auth-heavy types)
    reason_idx = np.zeros(n, dtype=int)
    for t in atype.unique():
        rows = np.where((atype == t).to_numpy() & denied)[0]
        if len(rows) == 0:
            continue
        w = np.array([r["weight"] * (AUTH_BOOST.get(t, 1.0) if r["carc"] == "197" else 1.0)
                      for r in DENIAL_REASONS])
        reason_idx[rows] = rng.choice(len(DENIAL_REASONS), size=len(rows), p=w / w.sum())

    carc = np.where(denied, np.array([r["carc"] for r in DENIAL_REASONS])[reason_idx], None)
    carc_desc = np.where(denied, np.array([r["desc"] for r in DENIAL_REASONS])[reason_idx], None)
    group = np.where(denied, np.array([r["group"] for r in DENIAL_REASONS])[reason_idx], None)

    # ---- 4. Final outcomes (the "truth", before as-of masking) -------------
    recover_p = np.array([r["recover"] for r in DENIAL_REASONS])[reason_idx]
    recovered = denied & (rng.random(n) < recover_p)
    unrecovered = denied & ~recovered
    pr_patient_pays = unrecovered & (group == "PR") & (rng.random(n) < PR_PATIENT_PAYS)
    written_off = unrecovered & ~pr_patient_pays
    payer_pays = ~denied | recovered

    allowed = expected_allowed.to_numpy()
    share = payer.map(lambda p: PAYER_PARAMS[p]["share"]).to_numpy()
    payer_paid = np.where(payer_pays, (allowed * (1 - share)).round(2), 0.0)
    patient_resp = np.where(payer_pays, (allowed - payer_paid).round(2),
                            np.where(pr_patient_pays, allowed, 0.0))
    patient_paid = np.where(
        payer_pays,
        np.where(rng.random(n) < PATIENT_PAY_RATE, patient_resp, 0.0),
        np.where(pr_patient_pays, allowed, 0.0),
    )

    extra = np.zeros(n, dtype=int)
    extra[recovered] = rng.integers(REWORK_DAYS[0], REWORK_DAYS[1] + 1, recovered.sum())
    closed = unrecovered
    extra[closed] = rng.integers(WRITEOFF_DAYS[0], WRITEOFF_DAYS[1] + 1, closed.sum())
    resolved = adjudicated + pd.to_timedelta(extra, unit="D")   # clean claims: same day

    # ---- 5. Mask to "as of" the last appointment date ----------------------
    is_adj = (adjudicated <= as_of).to_numpy()
    is_res = is_adj & (resolved <= as_of).to_numpy()

    remits = pd.DataFrame({
        "claim_id": claims["claim_id"],
        "adjudicated_date": to_dates(adjudicated),
        "resolved_date": to_dates(resolved.where(is_res)),
        "allowed": allowed,
        "denied": pd.array(denied, dtype="boolean"),
        "carc": carc,
        "carc_description": carc_desc,
        "group_code": group,
        "first_pass_paid": pd.array(~denied, dtype="boolean"),
        "recovered": pd.array(recovered, dtype="boolean"),
        "written_off": pd.array(written_off, dtype="boolean"),
        "payer_paid": payer_paid,
        "patient_responsibility": patient_resp,
        "patient_paid": patient_paid,
    })
    # Outcomes of denials still in progress are unknown, so blank them out
    for col in ["recovered", "written_off"]:
        remits.loc[~is_res, col] = pd.NA
    for col in ["payer_paid", "patient_responsibility", "patient_paid"]:
        remits.loc[~is_res, col] = np.nan
    remits = remits[is_adj].reset_index(drop=True)

    # ---- 6. Write to the database ------------------------------------------
    money = Numeric(10, 2)
    with engine.begin() as con:
        con.execute(text("DROP VIEW IF EXISTS claim_facts"))   # view blocks table replace
    claims.to_sql(
        "claims", engine, if_exists="replace", index=False, chunksize=10000,
        dtype={"claim_id": String(20), "appointment_id": String(20), "payer_id": String(10),
               "cpt_code": String(10), "billed": money, "expected_allowed": money,
               "submit_date": Date()},
    )
    remits.to_sql(
        "remittances", engine, if_exists="replace", index=False, chunksize=10000,
        dtype={"claim_id": String(20), "adjudicated_date": Date(), "resolved_date": Date(),
               "allowed": money, "denied": Boolean(), "carc": String(10),
               "carc_description": String(60), "group_code": String(4),
               "first_pass_paid": Boolean(), "recovered": Boolean(), "written_off": Boolean(),
               "payer_paid": money, "patient_responsibility": money, "patient_paid": money},
    )
    with engine.begin() as con:
        con.execute(text(VIEW_SQL.format(appts=APPOINTMENTS_TABLE)))

    # ---- 7. Sanity summary (matches the five dashboard metrics) -------------
    r = remits
    res = r[r["resolved_date"].notna()]
    print(f"as of {as_of.date()}: {n:,} claims, {len(r):,} adjudicated, {len(res):,} resolved")
    print(f"initial denial rate : {r['denied'].mean():.1%}  "
          f"(by $: {(r['allowed'] * r['denied']).sum() / r['allowed'].sum():.1%})")
    print(f"clean claim rate    : {r['first_pass_paid'].mean():.1%}")
    print(f"net collection rate : {(res['payer_paid'] + res['patient_paid']).sum() / res['allowed'].sum():.1%}")
    print(f"write-offs % of $   : {(res['allowed'] * res['written_off'].astype(float)).sum() / res['allowed'].sum():.1%}")


if __name__ == "__main__":
    main()
