from .session import engine
from .models import Location, Provider, Payer, Patient, Call, Appointment
from .base import Base

# JUST CALL ONCE TO CREATE TABLES
# python -m db.init_db

# If remake needed
# Base.metadata.drop_all(bind=engine)

Base.metadata.create_all(bind=engine)

print('Created all tables.')