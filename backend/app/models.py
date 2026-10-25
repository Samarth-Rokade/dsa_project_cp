"""
SQLAlchemy ORM models (the persistent source of truth).

blood_bags        one row per blood bag
hospital_requests one row per hospital request
dispatches        one row per processing attempt (append-only log)
dispatch_items    which bags were allocated in which dispatch
app_settings      small key/value table (expiry warning days, compatibility mode)
"""
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class BloodBag(Base):
    __tablename__ = "blood_bags"
    __table_args__ = (
        CheckConstraint("expiry_date > collection_date", name="ck_bag_expiry_after_collection"),
        Index("ix_bag_group_status", "blood_group", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bag_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    blood_group: Mapped[str] = mapped_column(String(3))
    collection_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date] = mapped_column(Date)
    volume_ml: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location: Mapped[str] = mapped_column(String(60), default="Central Blood Bank")
    status: Mapped[str] = mapped_column(String(12), default="available")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class HospitalRequest(Base):
    __tablename__ = "hospital_requests"
    __table_args__ = (
        CheckConstraint("units_needed > 0", name="ck_request_units_positive"),
        CheckConstraint("urgency_level IN (1, 2, 3)", name="ck_request_urgency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    hospital_name: Mapped[str] = mapped_column(String(80))
    required_blood_group: Mapped[str] = mapped_column(String(3))
    units_needed: Mapped[int] = mapped_column(Integer)
    units_allocated: Mapped[int] = mapped_column(Integer, default=0)
    urgency_level: Mapped[int] = mapped_column(Integer)
    arrival_sequence: Mapped[int] = mapped_column(Integer, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    notes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    dispatches: Mapped[List["Dispatch"]] = relationship(back_populates="request")


class Dispatch(Base):
    __tablename__ = "dispatches"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_pk: Mapped[int] = mapped_column(ForeignKey("hospital_requests.id"), index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    units_allocated: Mapped[int] = mapped_column(Integer, default=0)
    units_remaining: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[str] = mapped_column(String(20))          # fulfilled | partially_fulfilled | no_stock
    groups_considered: Mapped[str] = mapped_column(String(40), default="")
    decision_summary: Mapped[str] = mapped_column(Text, default="")

    request: Mapped["HospitalRequest"] = relationship(back_populates="dispatches")
    items: Mapped[List["DispatchItem"]] = relationship(back_populates="dispatch", cascade="all, delete-orphan")


class DispatchItem(Base):
    __tablename__ = "dispatch_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    dispatch_id: Mapped[int] = mapped_column(ForeignKey("dispatches.id"), index=True)
    blood_bag_pk: Mapped[int] = mapped_column(ForeignKey("blood_bags.id"))
    donor_blood_group: Mapped[str] = mapped_column(String(3))
    expiry_date_at_dispatch: Mapped[date] = mapped_column(Date)

    dispatch: Mapped["Dispatch"] = relationship(back_populates="items")
    bag: Mapped["BloodBag"] = relationship()


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(60))
