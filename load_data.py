import pandas as pd
from db.session import engine

def strip_text_columns(df):
    text_cols = df.select_dtypes(include=['object', 'string']).columns
    for col in text_cols:
        df[col] = df[col].str.strip()

def strip_column_titles(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    return df

def etl():
    # EXTRACT
    # load CSVs, clean column titles and text columns, return as dict
    locations_df = pd.read_csv("data/locations.csv")
    providers_df = pd.read_csv("data/providers.csv")
    payers_df = pd.read_csv("data/payers.csv")
    patients_df = pd.read_csv("data/patients.csv")
    calls_df = pd.read_csv("data/calls.csv")
    appointments_df = pd.read_csv("data/appointments.csv")


    # TRANSFORM
    for df in [locations_df, providers_df, payers_df, patients_df, calls_df, appointments_df]:
        strip_column_titles(df)
        strip_text_columns(df)

    # APPOINTMENTS
    # Add unknown provider to preserve values for joins to fix appointments
    # Better than dropping it and losing the data
    unknown_provider = pd.DataFrame([{
    'provider_id': 'UNK', 'provider_name': 'Unknown Provider',
    'specialty': 'Unknown', 'primary_location_id': None, 'hire_date': pd.NaT
    }])
    providers_df = pd.concat([providers_df, unknown_provider], ignore_index=True)

    # Set missing providers to 'UNK'
    invalid_provider_mask = ~appointments_df['provider_id'].isin(set(providers_df['provider_id']))
    appointments_df.loc[invalid_provider_mask, 'provider_id'] = 'UNK'

    appointments_df['date'] = pd.to_datetime(appointments_df['date'], errors='coerce', format='%Y-%m-%d')
    appointments_df['booked_date'] = pd.to_datetime(appointments_df['booked_date'], errors='coerce', format='%Y-%m-%d')

    # Correct impossible values, an appointment can't be booked after its own date
    bad_dates = appointments_df['booked_date'] > appointments_df['date']
    appointments_df.loc[bad_dates, 'booked_date'] = pd.NaT

    # Drop duplicate rows based on the 'appointment_id' column
    appointments_df.drop_duplicates(subset=['appointment_id'], keep='first', inplace=True)

    # PATIENTS
    patients_df['first_visit_date'] = pd.to_datetime(patients_df['first_visit_date'], errors='coerce', format='%Y-%m-%d')
    # Referral sources had an error with values that mean the same but inaccurate casing
    patients_df['referral_source'] = patients_df['referral_source'].str.strip().str.title()

    # PAYERS
    # Nothing needed

    # PROVIDERS
    providers_df['hire_date'] = pd.to_datetime(providers_df['hire_date'], errors='coerce', format='%Y-%m-%d')

    # LOCATIONS
    # Nothing needed

    # CALLS
    calls_df['date'] = pd.to_datetime(calls_df['date'], errors='coerce', format='%Y-%m-%d')


    # LOAD
    locations_df.to_sql('locations', con=engine, if_exists='append', index=False)
    providers_df.to_sql('providers', con=engine, if_exists='append', index=False)
    payers_df.to_sql('payers', con=engine, if_exists='append', index=False)
    patients_df.to_sql('patients', con=engine, if_exists='append', index=False)
    calls_df.to_sql('calls', con=engine, if_exists='append', index=False)
    appointments_df.to_sql('appointments', con=engine, if_exists='append', index=False)
    
    print('Load completed.')

if __name__ == '__main__':
    etl()