"""
Ortho Performance — Synthetic data generator v3
-------------------------------------------------
7 locations, 27 real providers, Jul 2022 – Sep 2026 (~4.25 years)

Realistic design decisions:
- Pasadena is the operational flagship (most providers, highest rev/visit)
- Santa Clarita is the original/founder office, solid but not dominant
- Monthly seasonal patterns (Jan/Feb dip, summer peak) applied to all locations
- Two disruption events baked in:
    * Burbank renovation closure: Feb 15 – Mar 31, 2024
    * Provider departure (David Rossi, Santa Clarita): leaves Jun 30, 2025
- Per-location and per-provider performance multipliers create genuine variance
- Same 5 seeded data quality issues, proportionally scaled
"""

import csv
import random
from datetime import date, timedelta

random.seed(42)

OUT_DIR = "data"
SEASON_START = date(2022, 7, 1)
SEASON_END   = date(2026, 9, 5)

# Disruption events
BURBANK_CLOSURE_START = date(2024, 2, 15)
BURBANK_CLOSURE_END   = date(2024, 3, 31)
ROSSI_DEPARTURE       = date(2025, 6, 30)   # David Rossi leaves Santa Clarita

# ---------------------------------------------------------------------------
# Seasonal multiplier — orthopedic-realistic
# ---------------------------------------------------------------------------
SEASONAL = {
    1: 0.82,   # January — deductible reset, patients delay elective procedures
    2: 0.87,   # February — still slow
    3: 0.96,   # March — picks up
    4: 1.00,   # April — baseline
    5: 1.04,   # May — school sports injuries ramping up
    6: 1.08,   # June — summer surge begins
    7: 1.12,   # July — peak: outdoor activity, surgery before school year
    8: 1.10,   # August — still strong
    9: 1.03,   # September — back to school, some slowdown
    10: 0.98,  # October — steady
    11: 0.95,  # November — holiday disruption
    12: 0.90,  # December — holidays, year-end deductible rush then drop
}

def growth_factor(d: date) -> float:
    if d < date(2023, 8, 1):
        return 0.55
    elif d < date(2024, 8, 1):
        return 0.78
    elif d < date(2025, 8, 1):
        return 1.00
    elif d < date(2026, 8, 1):
        return 1.18
    else:
        return 1.22

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------
locations = [
    {"location_id": "L1", "location_name": "Santa Clarita Office",  "city": "Santa Clarita", "state": "CA",
     "vol_mult": 0.95, "rev_adj":   5, "no_show_adj":  0.00},
    {"location_id": "L2", "location_name": "Valencia Office",       "city": "Valencia",      "state": "CA",
     "vol_mult": 1.00, "rev_adj":   8, "no_show_adj": -0.01},
    {"location_id": "L3", "location_name": "Burbank Office",        "city": "Burbank",       "state": "CA",
     "vol_mult": 1.05, "rev_adj":  12, "no_show_adj":  0.02},
    {"location_id": "L4", "location_name": "Glendale Office",       "city": "Glendale",      "state": "CA",
     "vol_mult": 0.55, "rev_adj":  10, "no_show_adj":  0.02},
    {"location_id": "L5", "location_name": "Pasadena Office",       "city": "Pasadena",      "state": "CA",
     "vol_mult": 1.05, "rev_adj":  18, "no_show_adj": -0.02},
    {"location_id": "L6", "location_name": "Thousand Oaks Office",  "city": "Thousand Oaks", "state": "CA",
     "vol_mult": 0.78, "rev_adj":   2, "no_show_adj":  0.01},
    {"location_id": "L7", "location_name": "Northridge Office",     "city": "Northridge",    "state": "CA",
     "vol_mult": 0.90, "rev_adj":  -2, "no_show_adj":  0.04},
]
location_csv_fields = ["location_id", "location_name", "city", "state"]
location_meta = {loc["location_id"]: loc for loc in locations}

# ---------------------------------------------------------------------------
# Providers — Pasadena now has the most (6), Santa Clarita drops to 4
# Provider P5 (David Rossi) departs Jun 30 2025 — tracked by departure date
# ---------------------------------------------------------------------------
provider_defs = [
    # Santa Clarita (L1) — 4 providers, original office
    {"first": "James",    "last": "Nguyen",    "specialty": "Orthopedic Surgery",        "location": "L1", "hire_offset": (0,  400), "vol_factor": 1.10, "rev_factor": 1.05, "no_show_base": 0.09, "departs": None},
    {"first": "Maria",    "last": "Patel",     "specialty": "Sports Medicine",           "location": "L1", "hire_offset": (0,  400), "vol_factor": 1.05, "rev_factor": 0.97, "no_show_base": 0.08, "departs": None},
    {"first": "Robert",   "last": "Garcia",    "specialty": "Spine Surgery",             "location": "L1", "hire_offset": (50, 500), "vol_factor": 1.00, "rev_factor": 1.22, "no_show_base": 0.10, "departs": None},
    {"first": "David",    "last": "Rossi",     "specialty": "Physical Medicine & Rehab", "location": "L1", "hire_offset": (0,  300), "vol_factor": 1.02, "rev_factor": 0.90, "no_show_base": 0.11, "departs": ROSSI_DEPARTURE},
    # Valencia (L2) — 4 providers
    {"first": "Susan",    "last": "Chen",      "specialty": "Orthopedic Surgery",        "location": "L2", "hire_offset": (0,  500), "vol_factor": 1.00, "rev_factor": 1.08, "no_show_base": 0.10, "departs": None},
    {"first": "Michael",  "last": "Alvarez",   "specialty": "Sports Medicine",           "location": "L2", "hire_offset": (100,600), "vol_factor": 1.05, "rev_factor": 0.95, "no_show_base": 0.11, "departs": None},
    {"first": "Karen",    "last": "Bennett",   "specialty": "Physical Therapy",          "location": "L2", "hire_offset": (200,700), "vol_factor": 0.95, "rev_factor": 0.72, "no_show_base": 0.13, "departs": None},
    {"first": "Thomas",   "last": "Walsh",     "specialty": "Pain Management",           "location": "L2", "hire_offset": (400,900), "vol_factor": 0.90, "rev_factor": 1.02, "no_show_base": 0.14, "departs": None},
    # Burbank (L3) — 5 providers, strong LA-adjacent location
    {"first": "Nancy",    "last": "Okafor",    "specialty": "Orthopedic Surgery",        "location": "L3", "hire_offset": (0,  400), "vol_factor": 1.08, "rev_factor": 1.10, "no_show_base": 0.12, "departs": None},
    {"first": "George",   "last": "Tanaka",    "specialty": "Hand & Upper Extremity",    "location": "L3", "hire_offset": (0,  400), "vol_factor": 1.00, "rev_factor": 1.18, "no_show_base": 0.13, "departs": None},
    {"first": "Patricia", "last": "Morales",   "specialty": "Sports Medicine",           "location": "L3", "hire_offset": (100,600), "vol_factor": 0.92, "rev_factor": 0.96, "no_show_base": 0.14, "departs": None},
    {"first": "Charles",  "last": "Nwosu",     "specialty": "Physical Therapy",          "location": "L3", "hire_offset": (200,700), "vol_factor": 1.00, "rev_factor": 0.73, "no_show_base": 0.15, "departs": None},
    {"first": "Barbara",  "last": "Johansson", "specialty": "Physical Medicine & Rehab", "location": "L3", "hire_offset": (400,800), "vol_factor": 0.85, "rev_factor": 0.91, "no_show_base": 0.14, "departs": None},
    # Glendale (L4) — 1 provider, satellite
    {"first": "Steven",   "last": "Park",      "specialty": "Orthopedic Surgery",        "location": "L4", "hire_offset": (850,1050),"vol_factor": 0.72, "rev_factor": 1.05, "no_show_base": 0.12, "departs": None},
    # Pasadena (L5) — 6 providers, operational flagship
    {"first": "Kenneth",  "last": "Hoffman",   "specialty": "Spine Surgery",             "location": "L5", "hire_offset": (0,  300), "vol_factor": 1.05, "rev_factor": 1.18, "no_show_base": 0.08, "departs": None},
    {"first": "Sandra",   "last": "Petrov",    "specialty": "Orthopedic Surgery",        "location": "L5", "hire_offset": (0,  300), "vol_factor": 1.00, "rev_factor": 1.08, "no_show_base": 0.08, "departs": None},
    {"first": "Edward",   "last": "Chukwu",    "specialty": "Hand & Upper Extremity",    "location": "L5", "hire_offset": (100,500), "vol_factor": 0.98, "rev_factor": 1.10, "no_show_base": 0.09, "departs": None},
    {"first": "Dorothy",  "last": "Reyes",     "specialty": "Sports Medicine",           "location": "L5", "hire_offset": (200,600), "vol_factor": 1.00, "rev_factor": 0.97, "no_show_base": 0.09, "departs": None},
    {"first": "Ashley",   "last": "Lindqvist", "specialty": "Physical Therapy",          "location": "L5", "hire_offset": (300,700), "vol_factor": 0.98, "rev_factor": 0.78, "no_show_base": 0.10, "departs": None},
    {"first": "Brian",    "last": "Osei",      "specialty": "Pain Management",           "location": "L5", "hire_offset": (500,900), "vol_factor": 0.92, "rev_factor": 1.02, "no_show_base": 0.11, "departs": None},
    # Thousand Oaks (L6) — 3 providers
    {"first": "Megan",    "last": "Schultz",   "specialty": "Sports Medicine",           "location": "L6", "hire_offset": (0,  500), "vol_factor": 0.80, "rev_factor": 0.97, "no_show_base": 0.11, "departs": None},
    {"first": "Daniel",   "last": "Castillo",  "specialty": "Orthopedic Surgery",        "location": "L6", "hire_offset": (200,600), "vol_factor": 0.75, "rev_factor": 1.05, "no_show_base": 0.12, "departs": None},
    {"first": "Amanda",   "last": "Ferreira",  "specialty": "Physical Medicine & Rehab", "location": "L6", "hire_offset": (400,800), "vol_factor": 0.70, "rev_factor": 0.88, "no_show_base": 0.13, "departs": None},
    # Northridge (L7) — 4 providers
    {"first": "Jason",    "last": "Mensah",    "specialty": "Orthopedic Surgery",        "location": "L7", "hire_offset": (0,  500), "vol_factor": 0.92, "rev_factor": 1.02, "no_show_base": 0.14, "departs": None},
    {"first": "Laura",    "last": "Diaz",      "specialty": "Hand & Upper Extremity",    "location": "L7", "hire_offset": (100,600), "vol_factor": 0.88, "rev_factor": 1.12, "no_show_base": 0.16, "departs": None},
    {"first": "Ryan",     "last": "Nakamura",  "specialty": "Sports Medicine",           "location": "L7", "hire_offset": (200,700), "vol_factor": 0.82, "rev_factor": 0.93, "no_show_base": 0.17, "departs": None},
    {"first": "Kimberly", "last": "Adeyemi",   "specialty": "Physical Therapy",          "location": "L7", "hire_offset": (400,800), "vol_factor": 0.85, "rev_factor": 0.74, "no_show_base": 0.15, "departs": None},
]

providers = []
for i, p in enumerate(provider_defs):
    lo, hi = p["hire_offset"]
    hire_date = SEASON_START + timedelta(days=random.randint(lo, hi))
    hire_date = min(hire_date, SEASON_END - timedelta(days=60))
    suffix = ", PT" if p["specialty"] == "Physical Therapy" else ""
    title  = "Dr. " if not suffix else ""
    providers.append({
        "provider_id":        f"P{i+1}",
        "provider_name":      f"{title}{p['first']} {p['last']}{suffix}",
        "specialty":          p["specialty"],
        "primary_location_id": p["location"],
        "hire_date":          hire_date.isoformat(),
        "_vol_factor":        p["vol_factor"],
        "_rev_factor":        p["rev_factor"],
        "_no_show_base":      p["no_show_base"],
        "_departs":           p["departs"],
        "_location_meta":     location_meta[p["location"]],
    })

# ---------------------------------------------------------------------------
# Payers
# ---------------------------------------------------------------------------
payers = [
    {"payer_id": "PY1", "payer_name": "Medicare",     "payer_type": "Medicare"},
    {"payer_id": "PY2", "payer_name": "Medi-Cal",     "payer_type": "Medicaid"},
    {"payer_id": "PY3", "payer_name": "Blue Cross",   "payer_type": "Commercial"},
    {"payer_id": "PY4", "payer_name": "Aetna",        "payer_type": "Commercial"},
    {"payer_id": "PY5", "payer_name": "Humana",       "payer_type": "Commercial"},
    {"payer_id": "PY6", "payer_name": "Self-Pay",     "payer_type": "Self-Pay"},
    {"payer_id": "PY7", "payer_name": "UnitedHealth", "payer_type": "Commercial"},
]
payer_weights = [0.18, 0.10, 0.20, 0.13, 0.10, 0.12, 0.17]

referral_sources = ["Physician Referral", "Self", "Insurance Directory", "Online Search", "Friend/Family"]
referral_weights  = [0.42, 0.20, 0.14, 0.14, 0.10]
referral_source_dirty_variants = {
    "Self":               ["self", "SELF", " Self "],
    "Physician Referral": ["physician referral", "Physician referral "],
}

# ---------------------------------------------------------------------------
# Appointment types — specialty-biased weights
# ---------------------------------------------------------------------------
appt_types_base = {
    "New Patient Consult": (0.14, (190, 340), (1.9, 2.8), True,  12),
    "Follow-up":          (0.44, (75,  150), (0.6, 1.2), False,  8),
    "Post-Op Check":      (0.14, (60,  105), (0.5, 0.8), False,  5),
    "Physical Therapy":   (0.19, (85,  165), (0.8, 1.4), False,  6),
    "Injection/Procedure":(0.09, (260, 650), (2.6, 5.0), False,  8),
}

def appt_type_weights_for(specialty):
    w = {k: v[0] for k, v in appt_types_base.items()}
    if "Surgery" in specialty or "Hand" in specialty:
        w["Injection/Procedure"] *= 1.8; w["Post-Op Check"] *= 1.6; w["Physical Therapy"] *= 0.5
    elif specialty == "Physical Therapy":
        w["Physical Therapy"] *= 3.0; w["New Patient Consult"] *= 0.5; w["Injection/Procedure"] *= 0.1
    elif specialty == "Pain Management":
        w["Injection/Procedure"] *= 2.5; w["Follow-up"] *= 0.8
    elif specialty == "Sports Medicine":
        w["New Patient Consult"] *= 1.3; w["Injection/Procedure"] *= 1.2
    total = sum(w.values())
    return [w[k] / total for k in appt_types_base]

type_names = list(appt_types_base.keys())

call_types = ["New Patient Inquiry", "Reschedule", "Billing Question", "General Inquiry"]
call_type_weights = [0.34, 0.31, 0.15, 0.20]
call_outcomes_by_type = {
    "New Patient Inquiry": (["Booked", "Not Booked"],    [0.63, 0.37]),
    "Reschedule":          (["Booked", "Not Booked"],    [0.84, 0.16]),
    "Billing Question":    (["Info Only"],               [1.00]),
    "General Inquiry":     (["Info Only", "Not Booked"], [0.80, 0.20]),
}

# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------
patients       = []
patients_by_id = {}
patient_counter = 1
appointments   = []
appt_id        = 1
calls          = []
call_id        = 1

current = SEASON_START
while current <= SEASON_END:
    if current.weekday() != 6:
        is_saturday  = current.weekday() == 5
        weekend_mult = 0.45 if is_saturday else 1.0
        seasonal     = SEASONAL[current.month]
        growth       = growth_factor(current)

        for loc in locations:
            # Burbank renovation closure
            if loc["location_id"] == "L3" and BURBANK_CLOSURE_START <= current <= BURBANK_CLOSURE_END:
                continue  # location is closed, no calls or appointments

            loc_day = weekend_mult * seasonal * growth * loc["vol_mult"]
            n_calls = max(0, int(random.gauss(8, 2.5) * loc_day))
            for _ in range(n_calls):
                ct = random.choices(call_types, weights=call_type_weights, k=1)[0]
                outs, ow = call_outcomes_by_type[ct]
                outcome = random.choices(outs, weights=ow, k=1)[0]
                calls.append({
                    "call_id": f"C{call_id}", "date": current.isoformat(),
                    "location_id": loc["location_id"], "call_type": ct,
                    "outcome": outcome, "handle_time_sec": random.randint(40, 510),
                })
                call_id += 1

        for provider in providers:
            if current < date.fromisoformat(provider["hire_date"]):
                continue
            # Provider departure
            if provider["_departs"] and current > provider["_departs"]:
                continue
            # Burbank provider: no appointments during closure
            if provider["_location_meta"]["location_id"] == "L3" and \
               BURBANK_CLOSURE_START <= current <= BURBANK_CLOSURE_END:
                continue

            loc_meta  = provider["_location_meta"]
            prov_vol  = provider["_vol_factor"]
            prov_rev  = provider["_rev_factor"]
            prov_nsr  = max(0.04, min(0.30, provider["_no_show_base"] + loc_meta["no_show_adj"]))
            p_weights = appt_type_weights_for(provider["specialty"])
            loc_day   = weekend_mult * seasonal * growth * loc_meta["vol_mult"] * prov_vol

            n_appts = max(0, int(random.gauss(10, 2.5) * loc_day))
            for _ in range(n_appts):
                atype = random.choices(type_names, weights=p_weights, k=1)[0]
                _, rev_range, rvu_range, is_new, lead_mean = appt_types_base[atype]

                if is_new or not patients:
                    payer = random.choices(payers, weights=payer_weights, k=1)[0]
                    ref   = random.choices(referral_sources, weights=referral_weights, k=1)[0]
                    pat   = {"patient_id": f"PT{patient_counter}",
                             "first_visit_date": current.isoformat(),
                             "referral_source": ref, "payer_id": payer["payer_id"]}
                    patients.append(pat); patients_by_id[pat["patient_id"]] = pat
                    patient_counter += 1
                else:
                    pat = random.choice(patients)

                roll = random.random()
                if roll < prov_nsr:            status = "No-Show"
                elif roll < prov_nsr + 0.05:  status = "Cancelled"
                else:                          status = "Completed"

                if status == "Completed":
                    base_rev = random.uniform(*rev_range)
                    revenue  = round(max(20.0, (base_rev + loc_meta["rev_adj"]) * prov_rev), 2)
                    rvu      = round(random.uniform(*rvu_range) * prov_rev, 2)
                else:
                    revenue = 0.0; rvu = 0.0

                loc_id = provider["_location_meta"]["location_id"] if random.random() > 0.08 \
                    else random.choice(locations)["location_id"]
                lead_days   = max(0, int(random.gauss(lead_mean, 5)))
                booked_date = current - timedelta(days=lead_days)

                appointments.append({
                    "appointment_id": f"A{appt_id}", "date": current.isoformat(),
                    "booked_date": booked_date.isoformat(),
                    "provider_id": provider["provider_id"], "location_id": loc_id,
                    "patient_id": pat["patient_id"], "payer_id": pat["payer_id"],
                    "appointment_type": atype, "is_new_patient": is_new,
                    "status": status, "revenue": revenue, "rvu": rvu,
                })
                appt_id += 1

    current += timedelta(days=1)

# ---------------------------------------------------------------------------
# Inject data quality issues
# ---------------------------------------------------------------------------
def inject_dq(appointments, patients):
    notes = []

    n = max(1, int(len(appointments) * 0.005))
    appointments.extend([dict(r) for r in random.sample(appointments, n)])
    notes.append(f"{n} duplicate appointment rows.")

    comp = [a for a in appointments if a["status"] == "Completed"]
    n = max(1, int(len(comp) * 0.01))
    for r in random.sample(comp, n): r["revenue"] = ""
    notes.append(f"{n} Completed appointments with blank revenue.")

    dirty = [p for p in patients if p["referral_source"] in referral_source_dirty_variants]
    n = max(1, int(len(dirty) * 0.08))
    for p in random.sample(dirty, min(n, len(dirty))):
        p["referral_source"] = random.choice(referral_source_dirty_variants[p["referral_source"]])
    notes.append(f"~{n} patients with inconsistent referral_source casing/whitespace.")

    n = max(1, int(len(appointments) * 0.003))
    for r in random.sample(appointments, n): r["provider_id"] = "P99"
    notes.append(f"{n} appointments reference non-existent provider_id 'P99'.")

    n = max(1, int(len(appointments) * 0.002))
    for r in random.sample(appointments, n):
        d = date.fromisoformat(r["date"])
        r["booked_date"] = (d + timedelta(days=random.randint(1, 10))).isoformat()
    notes.append(f"{n} appointments where booked_date is after appointment date.")

    return notes

dq_notes = inject_dq(appointments, patients)

# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------
def write_csv(filename, rows, fields):
    with open(f"{OUT_DIR}/{filename}", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

write_csv("locations.csv",    locations,    location_csv_fields)
write_csv("providers.csv",    providers,    ["provider_id","provider_name","specialty","primary_location_id","hire_date"])
write_csv("payers.csv",       payers,       ["payer_id","payer_name","payer_type"])
write_csv("patients.csv",     patients,     ["patient_id","first_visit_date","referral_source","payer_id"])
write_csv("calls.csv",        calls,        ["call_id","date","location_id","call_type","outcome","handle_time_sec"])
write_csv("appointments.csv", appointments, ["appointment_id","date","booked_date","provider_id","location_id",
                                             "patient_id","payer_id","appointment_type","is_new_patient","status","revenue","rvu"])

print(f"locations:    {len(locations)}")
print(f"providers:    {len(providers)} real + 1 UNK added during ETL")
print(f"payers:       {len(payers)}")
print(f"patients:     {len(patients)}")
print(f"calls:        {len(calls)}")
print(f"appointments: {len(appointments)}")
print("\nSeeded issues:")
for n in dq_notes: print(f"  - {n}")
