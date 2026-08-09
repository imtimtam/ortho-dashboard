"""
Synthetic data generator for the orthopedic practice analytics project.

Produces six CSVs: locations, providers, payers, patients, calls,
appointments -- plus a small, DELIBERATE, documented set of data quality
issues (see inject_data_quality_issues() and DATA_QUALITY_NOTES.md) so
there's something real to clean, not just charts to build.
"""

import csv
import random
from datetime import date, timedelta

random.seed(42)  # reproducible -- rerun and get the same dataset

OUT_DIR = "data"
SEASON_START = date(2023, 8, 1)
SEASON_END = date(2026, 7, 31)

# Rough practice-growth trend by season-year, so YoY comparisons show
# something real rather than flat noise. Applied as a multiplier on
# daily appointment/call volume.
def year_growth_factor(d: date) -> float:
    if d < date(2024, 8, 1):
        return 0.80   # Aug 2023 - Jul 2024
    elif d < date(2025, 8, 1):
        return 1.00   # Aug 2024 - Jul 2025 (baseline)
    else:
        return 1.18   # Aug 2025 - Jul 2026 (current, busiest)

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------
locations = [
    {"location_id": "L1", "location_name": "Santa Clarita Office", "city": "Santa Clarita", "state": "CA"},
    {"location_id": "L2", "location_name": "Valencia Office", "city": "Valencia", "state": "CA"},
    {"location_id": "L3", "location_name": "Burbank Office", "city": "Burbank", "state": "CA"},
    {"location_id": "L4", "location_name": "Glendale Office", "city": "Glendale", "state": "CA"},
]

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
first_names = ["James", "Maria", "Robert", "Linda", "David", "Susan", "Michael", "Karen"]
last_names = ["Nguyen", "Patel", "Garcia", "Kim", "Rossi", "Chen", "Alvarez", "Bennett"]
specialties = [
    "Orthopedic Surgery", "Orthopedic Surgery", "Sports Medicine",
    "Sports Medicine", "Physical Medicine & Rehab", "Physical Therapy",
    "Pain Management", "Orthopedic Surgery",
]

providers = []
# Uneven distribution: Santa Clarita (main office) gets 3, Valencia and
# Burbank get 2 each, Glendale (newest, smallest) gets 1 -- real practices
# have a flagship location, not an even split.
location_assignment = ["L1", "L1", "L1", "L2", "L2", "L3", "L3", "L4"]

for i in range(8):
    is_glendale = location_assignment[i] == "L4"
    if is_glendale:
        # Glendale is the newest office -- its one provider was hired
        # within the last year of the dataset, not spread across 5 years
        hire_date = (date(2025, 8, 1) + timedelta(days=random.randint(0, 300))).isoformat()
    else:
        hire_date = (date(2019, 1, 1) + timedelta(days=random.randint(0, 2000))).isoformat()

    providers.append({
        "provider_id": f"P{i+1}",
        "provider_name": f"Dr. {first_names[i]} {last_names[i]}" if specialties[i] != "Physical Therapy"
                          else f"{first_names[i]} {last_names[i]}, PT",
        "specialty": specialties[i],
        "primary_location_id": location_assignment[i],
        "hire_date": hire_date,
    })

# ---------------------------------------------------------------------------
# Payers
# ---------------------------------------------------------------------------
payers = [
    {"payer_id": "PY1", "payer_name": "Medicare", "payer_type": "Medicare"},
    {"payer_id": "PY2", "payer_name": "Medi-Cal", "payer_type": "Medicaid"},
    {"payer_id": "PY3", "payer_name": "Blue Cross", "payer_type": "Commercial"},
    {"payer_id": "PY4", "payer_name": "Aetna", "payer_type": "Commercial"},
    {"payer_id": "PY5", "payer_name": "Humana", "payer_type": "Commercial"},
    {"payer_id": "PY6", "payer_name": "Self-Pay", "payer_type": "Self-Pay"},
]
payer_weights = [0.22, 0.13, 0.22, 0.16, 0.12, 0.15]

referral_sources = ["Physician Referral", "Self", "Insurance Directory", "Online Search", "Friend/Family"]
referral_weights = [0.40, 0.20, 0.15, 0.15, 0.10]

# messy variants deliberately introduced later for a subset of rows
referral_source_dirty_variants = {
    "Self": ["self", "SELF", " Self "],
    "Physician Referral": ["physician referral", "Physician referral "],
}

# ---------------------------------------------------------------------------
# Appointment type definitions
# ---------------------------------------------------------------------------
appt_types = {
    # type: (weight, revenue_range, rvu_range, is_new_patient, lead_time_mean_days)
    "New Patient Consult": (0.15, (180, 320), (1.8, 2.6), True, 12),
    "Follow-up": (0.45, (70, 140), (0.6, 1.1), False, 9),
    "Post-Op Check": (0.15, (60, 100), (0.5, 0.8), False, 5),
    "Physical Therapy": (0.20, (90, 160), (0.9, 1.4), False, 6),
    "Injection/Procedure": (0.05, (250, 600), (2.5, 4.5), False, 8),
}
type_names = list(appt_types.keys())
type_weights = [v[0] for v in appt_types.values()]

call_types = ["New Patient Inquiry", "Reschedule", "Billing Question", "General Inquiry"]
call_type_weights = [0.35, 0.30, 0.15, 0.20]
call_outcomes_by_type = {
    "New Patient Inquiry": (["Booked", "Not Booked"], [0.62, 0.38]),
    "Reschedule": (["Booked", "Not Booked"], [0.85, 0.15]),
    "Billing Question": (["Info Only"], [1.0]),
    "General Inquiry": (["Info Only", "Not Booked"], [0.8, 0.2]),
}

# ---------------------------------------------------------------------------
# Generate patients + appointments together, day by day
# (patients are created the day they first show up as a New Patient Consult)
# ---------------------------------------------------------------------------
patients = []          # list of dicts
patients_by_id = {}    # patient_id -> dict, for quick lookup of existing patients
patient_counter = 1

appointments = []
appt_id = 1

calls = []
call_id = 1

current = SEASON_START
while current <= SEASON_END:
    if current.weekday() != 6:  # closed Sundays
        day_factor = 1.0 if current.weekday() < 5 else 0.4  # lighter Saturdays
        day_factor *= year_growth_factor(current)

        # --- calls for the day, per location ---
        for loc in locations:
            n_calls = max(0, int(random.gauss(9, 3) * day_factor))
            for _ in range(n_calls):
                ctype = random.choices(call_types, weights=call_type_weights, k=1)[0]
                outcomes, outcome_w = call_outcomes_by_type[ctype]
                outcome = random.choices(outcomes, weights=outcome_w, k=1)[0]
                calls.append({
                    "call_id": f"C{call_id}",
                    "date": current.isoformat(),
                    "location_id": loc["location_id"],
                    "call_type": ctype,
                    "outcome": outcome,
                    "handle_time_sec": random.randint(45, 480),
                })
                call_id += 1

        # --- appointments for the day, per provider ---
        for provider in providers:
            if current < date.fromisoformat(provider["hire_date"]):
                continue  # provider not yet hired -- can't have appointments
            n_appts = max(0, int(random.gauss(11, 3) * day_factor))
            for _ in range(n_appts):
                appt_type = random.choices(type_names, weights=type_weights, k=1)[0]
                _, rev_range, rvu_range, is_new, lead_mean = appt_types[appt_type]

                # pick or create a patient
                if is_new or not patients:
                    payer = random.choices(payers, weights=payer_weights, k=1)[0]
                    ref_source = random.choices(referral_sources, weights=referral_weights, k=1)[0]
                    patient = {
                        "patient_id": f"PT{patient_counter}",
                        "first_visit_date": current.isoformat(),
                        "referral_source": ref_source,
                        "payer_id": payer["payer_id"],
                    }
                    patients.append(patient)
                    patients_by_id[patient["patient_id"]] = patient
                    patient_counter += 1
                else:
                    patient = random.choice(patients)

                # no-show rate varies slightly by provider to create real spread
                no_show_base = 0.10 + (hash(provider["provider_id"]) % 10) / 100
                roll = random.random()
                if roll < no_show_base:
                    status = "No-Show"
                elif roll < no_show_base + 0.05:
                    status = "Cancelled"
                else:
                    status = "Completed"

                revenue = round(random.uniform(*rev_range), 2) if status == "Completed" else 0.0
                rvu = round(random.uniform(*rvu_range), 2) if status == "Completed" else 0.0

                location_id = provider["primary_location_id"] if random.random() > 0.1 \
                    else random.choice(locations)["location_id"]

                lead_days = max(0, int(random.gauss(lead_mean, 5)))
                booked_date = current - timedelta(days=lead_days)

                appointments.append({
                    "appointment_id": f"A{appt_id}",
                    "date": current.isoformat(),
                    "booked_date": booked_date.isoformat(),
                    "provider_id": provider["provider_id"],
                    "location_id": location_id,
                    "patient_id": patient["patient_id"],
                    "payer_id": patient["payer_id"],
                    "appointment_type": appt_type,
                    "is_new_patient": is_new,
                    "status": status,
                    "revenue": revenue,
                    "rvu": rvu,
                })
                appt_id += 1
    current += timedelta(days=1)


# ---------------------------------------------------------------------------
# Inject a small, controlled, documented set of data quality issues
# ---------------------------------------------------------------------------
def inject_data_quality_issues(appointments, patients):
    notes = []

    # 1. ~0.5% duplicate appointment rows (simulates a scheduling-system re-sync)
    n_dupes = max(1, int(len(appointments) * 0.005))
    dupe_sample = random.sample(appointments, n_dupes)
    appointments.extend([dict(row) for row in dupe_sample])
    notes.append(f"{n_dupes} duplicate appointment rows (same appointment_id appears twice) "
                  f"-- simulates a scheduling-system re-sync.")

    # 2. ~1% missing revenue on Completed appointments (billing not yet posted)
    completed = [a for a in appointments if a["status"] == "Completed"]
    n_missing = max(1, int(len(completed) * 0.01))
    for row in random.sample(completed, n_missing):
        row["revenue"] = ""  # blank, not 0 -- these are different meanings
    notes.append(f"{n_missing} Completed appointments with blank revenue "
                  f"-- simulates billing not yet posted at time of export. "
                  f"Blank is NOT the same as $0 and should not be treated as zero.")

    # 3. Inconsistent casing/whitespace on referral_source (manual front-desk entry)
    dirty_candidates = [p for p in patients if p["referral_source"] in referral_source_dirty_variants]
    n_dirty = max(1, int(len(dirty_candidates) * 0.08))
    for patient in random.sample(dirty_candidates, min(n_dirty, len(dirty_candidates))):
        variants = referral_source_dirty_variants[patient["referral_source"]]
        patient["referral_source"] = random.choice(variants)
    notes.append(f"~{n_dirty} patients with inconsistent casing/whitespace in referral_source "
                  f"(e.g. 'self' / 'SELF' / ' Self ') -- simulates manual front-desk entry.")

    # 4. Orphaned provider_id -- a provider who left mid-year, ~0.3% of appointments
    n_orphan = max(1, int(len(appointments) * 0.003))
    for row in random.sample(appointments, n_orphan):
        row["provider_id"] = "P99"
    notes.append(f"{n_orphan} appointments reference provider_id 'P99', which does not exist "
                  f"in providers.csv -- simulates a provider who left the practice mid-year "
                  f"and whose historical records weren't reconciled.")

    # 5. booked_date after appointment date (data-entry logic error), ~0.2%
    n_bad_dates = max(1, int(len(appointments) * 0.002))
    for row in random.sample(appointments, n_bad_dates):
        appt_date = date.fromisoformat(row["date"])
        row["booked_date"] = (appt_date + timedelta(days=random.randint(1, 10))).isoformat()
    notes.append(f"{n_bad_dates} appointments where booked_date falls AFTER the appointment date "
                  f"-- simulates a data-entry logic error, not something that should be possible.")

    return notes


dq_notes = inject_data_quality_issues(appointments, patients)


# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------
def write_csv(filename, rows, fieldnames):
    with open(f"{OUT_DIR}/{filename}", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

write_csv("locations.csv", locations, ["location_id", "location_name", "city", "state"])
write_csv("providers.csv", providers, ["provider_id", "provider_name", "specialty", "primary_location_id", "hire_date"])
write_csv("payers.csv", payers, ["payer_id", "payer_name", "payer_type"])
write_csv("patients.csv", patients, ["patient_id", "first_visit_date", "referral_source", "payer_id"])
write_csv("calls.csv", calls, ["call_id", "date", "location_id", "call_type", "outcome", "handle_time_sec"])
write_csv("appointments.csv", appointments,
          ["appointment_id", "date", "booked_date", "provider_id", "location_id", "patient_id",
           "payer_id", "appointment_type", "is_new_patient", "status", "revenue", "rvu"])

# write the data quality notes alongside the data
with open("DATA_QUALITY_NOTES.md", "w") as f:
    f.write("# Seeded Data Quality Issues\n\n")
    f.write("This synthetic dataset has the following issues deliberately introduced, "
            "so there's something real to find and clean rather than starting from a "
            "perfectly clean file:\n\n")
    for i, note in enumerate(dq_notes, 1):
        f.write(f"{i}. {note}\n")

print(f"locations: {len(locations)} rows")
print(f"providers: {len(providers)} rows")
print(f"payers: {len(payers)} rows")
print(f"patients: {len(patients)} rows")
print(f"calls: {len(calls)} rows")
print(f"appointments: {len(appointments)} rows")
print("\nData quality issues seeded:")
for note in dq_notes:
    print(f"  - {note}")
