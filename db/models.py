from datetime import date as dt_date
from sqlalchemy import String, Date, Numeric, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base


class Location(Base):
    __tablename__ = "locations"

    location_id: Mapped[str] = mapped_column(String, primary_key=True)
    location_name: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)


class Provider(Base):
    __tablename__ = "providers"

    provider_id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    specialty: Mapped[str] = mapped_column(String, nullable=False)

    # nullable=True to accommodate the 'UNK' unknown-provider row, which
    # has no real location or hire date
    # better than completely dropping it and losing the data
    primary_location_id: Mapped[str | None] = mapped_column(String, ForeignKey("locations.location_id"), nullable=True)
    hire_date: Mapped[dt_date | None] = mapped_column(Date, nullable=True)


class Payer(Base):
    __tablename__ = "payers"

    payer_id: Mapped[str] = mapped_column(String, primary_key=True)
    payer_name: Mapped[str] = mapped_column(String, nullable=False)
    payer_type: Mapped[str] = mapped_column(String, nullable=False)


class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(String, primary_key=True)
    first_visit_date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    referral_source: Mapped[str] = mapped_column(String, nullable=False)
    payer_id: Mapped[str] = mapped_column(String, ForeignKey("payers.payer_id"), nullable=False)


class Call(Base):
    __tablename__ = "calls"

    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[dt_date] = mapped_column(Date, nullable=False)
    location_id: Mapped[str] = mapped_column(String, ForeignKey("locations.location_id"), nullable=False)
    call_type: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    handle_time_sec: Mapped[int] = mapped_column(Integer, nullable=False)


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[dt_date] = mapped_column(Date, nullable=False)

    # nullable=True because a small number of rows have booked_date AFTER
    # the appointment date -- a real data-entry error, cleaned by nulling
    # it out rather than guessing at the correct value
    booked_date: Mapped[dt_date | None] = mapped_column(Date, nullable=True)

    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.provider_id"), nullable=False)
    location_id: Mapped[str] = mapped_column(ForeignKey("locations.location_id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.patient_id"), nullable=False)
    payer_id: Mapped[str] = mapped_column(ForeignKey("payers.payer_id"), nullable=False)

    appointment_type: Mapped[str] = mapped_column(String, nullable=False)
    is_new_patient: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)

    # nullable=True -- NULL means "not yet posted," a different fact than $0
    revenue: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    rvu: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)