# Orthopedic Healthcare Performance Dashboard

![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=flat&logo=powerbi&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat&logo=postgresql&logoColor=white)
![DAX](https://img.shields.io/badge/DAX-217346?style=flat)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikit-learn&logoColor=white)
![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)

<p align="center">
  <img src="./images/ortho_overview.png" alt="Power BI Overview Dashboard" />
  <br>
  <em>Analysis overview generated in Power BI.</em>
  <br><br>
  <img src="./images/ortho_locations.png" alt="Power BI Office Location Dashboard" />
  <br>
  <em>A breakdown across orthopedic locations across Southern California.</em>
</p>

An interactive Power BI dashboard designed to analyze the operational
and financial performance of an orthopedic healthcare organization
across locations, providers, appointments, and payer types.

The project focuses on turning relational healthcare data into a clean
executive-facing analytics experience while demonstrating practical data
modeling, DAX, time-intelligence, and dashboard design.

## Dashboard Overview

The report is organized into five analytical pages:

  -----------------------------------------------------------------------
  Page                                Purpose
  ----------------------------------- -----------------------------------
  **Overview**                        High-level operational and
                                      financial performance

  **Providers**                       Provider productivity and
                                      appointment-level performance

  **Locations**                       Comparison of performance across
                                      locations

  **Revenue & Payers**                Revenue trends and payer mix

  **Growth**                          Period-over-period performance and
                                      growth metrics
  -----------------------------------------------------------------------

## Key Business Questions

The dashboard is designed to help answer questions such as:

-   How is overall revenue changing over time?
-   Which locations generate the most revenue and appointments?
-   Which providers have the highest appointment and revenue
    productivity?
-   How does payer mix affect revenue?
-   How are Medicare, Medicaid, commercial, and self-pay revenues
    distributed?
-   Are appointment volumes and revenue growing consistently?
-   How many new patients are being acquired?
-   Where are no-show or lead-time issues occurring?
-   How effectively are incoming calls converting into booked
    appointments?
-   How does performance change between selected periods?

### Key Metrics

The dashboard includes metrics such as:

-   Total Revenue
-   Total RVU
-   Total Appointments
-   New Patients
-   No-Show Rate
-   Average Lead Time
-   Median Lead Time
-   Average Revenue per Completed Appointment
-   Median Revenue per Completed Appointment
-   Average Revenue per RVU
-   Call-to-Booking Rate
-   New Patient Conversion
-   Revenue by Payer Type
-   Revenue and appointment trends
-   Location-level performance and growth
-   Provider-level productivity

## Interactive Analysis

A shared **Period Selector** allows users to analyze performance across
predefined time windows:

**1W · 1M · 3M · 6M · YTD · 1Y · ALL**

The period selection dynamically drives the dashboard's period-based
metrics and trend analysis.

The report also supports filtering by relevant dimensions such as:

-   Location
-   Provider
-   Specialty
-   Appointment Type
-   Payer
-   Referral Source
-   Date

## Data Model

The report uses a relational model centered around appointment activity.

### Core Tables

-   `public appointments` --- appointment dates, status, revenue, RVU,
    location, provider, and appointment type
-   `public patients` --- patient information and first-visit/referral
    attributes
-   `public providers` --- provider information, specialty, and primary
    location
-   `public locations` --- location names and geographic attributes
-   `public payers` --- payer names and payer classifications
-   `public calls` --- call activity, call type, and outcomes
-   `Date` --- dedicated calendar/date dimension used for time-based
    analysis, generated through Bravo

The model uses relationships between these entities to allow
operational, financial, and patient metrics to respond consistently to
report filters.

## Project Structure
```
ortho-dashboard/
│
├── bi/
│   └── ortho_bi.pbix            # Power BI dashboard for visual exploration
├── data/                        # Must be generated with `generate_data.py`
│   ├── appointments.csv
│   ├── calls.csv
│   ├── locations.csv
│   ├── patients.csv
│   ├── payers.csv
│   └── providers.csv
├── db/                          # Connect with Postgres
│   ├── __init__.py              
│   ├── base.py
│   ├── init_db.py
│   ├── models.py
│   └── session.py
├── images/                      # Images for previews and README
│   ├── ortho_growth.png            
│   ├── ortho_locations.png   
│   ├── ortho_overview.png   
│   ├── ortho_payers.png   
│   └── ortho_providers.png              
├── notebook/                    # Notebook for exploratory data analysis and machine-learning testing with scikit-learn
│   ├── data_cleaning.ipynb           
│   └── no_show_model.ipynb
├── generate_data.py             # Generate synthetic data due to privacy concerns with real data
├── load_data.py                 # Bulk load and transform data to connected Postgres database
├── README.md
└── requirements.txt
```

## How to Use

1. Open `bi\ortho_bi.pbix` in Power BI Desktop to interact with the dashboard.  

### Optional

2. Run `generate_data.py` to recreate the datasets with the current seed. This generator is freely modifiable to produce similar data with different scopes.
3. Review `db\` and `notebook\` folders to uncover the process of transforming and loading the data through Pandas and SQLAlchemy to PostgreSQL

## Tools Used
- **PostgreSQL**: Querying and validating synthetic data across 199076 appointments, 47551 calls, 25858 patients, 7 payers, 27 providers, and 7 locations across Southern California
- **Power BI**: Interactive dashboard visualizing performance across orthopedic offices along with calculations and measures for revenue, providers, locations, payers, and growth

## License

This project is licensed under the MIT License.

## Credits and Data Sources
The dataset used in this project is synthetic data generated with assistance from Anthropic's Claude and iteratively refined through prompt engineering to produce realistic healthcare operations, appointment, provider, location, payer, and financial patterns.

The data was intentionally designed and adjusted to support the analytical questions addressed by the dashboard. It does not represent real patients, providers, healthcare organizations, or actual financial performance.

The Power BI data model, DAX measures, time-intelligence logic, visualizations, dashboard design, and analytical framework were developed as part of this project.