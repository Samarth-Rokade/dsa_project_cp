"""Shared test fixtures: a fresh in-memory SQLite database and fresh in-memory structures per test."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base, get_db
from app.domain.state import InMemoryState, get_state
from app.main import app
from app.models import BloodBag, HospitalRequest

TODAY = date.today()


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def state(db):
    s = InMemoryState()
    s.rebuild(db)
    return s


@pytest.fixture
def client(session_factory, state):
    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_state] = lambda: state
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- helpers used by several test files ----------
def add_bag(db, state, bag_id, group, days_to_expiry, status="available"):
    expiry = TODAY + timedelta(days=days_to_expiry)
    bag = BloodBag(
        bag_id=bag_id, blood_group=group, collection_date=expiry - timedelta(days=42),
        expiry_date=expiry, volume_ml=450, location="Test Bank", status=status,
    )
    db.add(bag)
    db.commit()
    state.add_bag(bag)
    return bag


def add_request(db, state, group, units, urgency, hospital="Test Hospital"):
    seq = (db.query(HospitalRequest).count()) + 1
    req = HospitalRequest(
        request_id=f"REQ-{seq:04d}", hospital_name=hospital, required_blood_group=group,
        units_needed=units, units_allocated=0, urgency_level=urgency, arrival_sequence=seq, status="pending",
    )
    db.add(req)
    db.commit()
    state.add_request(req)
    return req
