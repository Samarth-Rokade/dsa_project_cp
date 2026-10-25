"""
Synthetic demo data (no real people, no real hospitals).

Dates are relative to "today" so the demo always has stock that expires soon, stock that
is already expired, and so on. Designed so that clicking "Process Next Request" six times
shows every outcome:

    click 1  REQ-0003  critical O-            -> fulfilled   (2 O- bags, earliest expiry first)
    click 2  REQ-0007  critical A+, 1 unit    -> fulfilled   using an O+ bag: it expires sooner (alternative group)
    click 3  REQ-0004  surgery B+, 8 units    -> partial     (5 compatible bags exist)
    click 4  REQ-0002  routine A+, 3 units    -> fulfilled   (two A+ bags share an expiry date: tie-break by bag ID)
                                                REQ-0004 and REQ-0005 are skipped: no stock, they stay pending
    click 5  REQ-0006  routine AB+, 2 units   -> partial     (only 1 AB+ bag left)
    click 6  nothing can be allocated         -> "no stock" logged, shortage shown
"""
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .constants import DEFAULT_SETTINGS
from .models import AppSetting, BloodBag, Dispatch, DispatchItem, HospitalRequest

# (bag_id, group, days until expiry, status, location, volume)
BAGS = [
    ("BAG-1001", "O-", 4, "available", "Central Blood Bank", 450),
    ("BAG-1002", "O-", 9, "available", "North Branch", 450),
    ("BAG-1003", "O-", -3, "available", "Central Blood Bank", 450),    # past expiry, row still 'available'
    ("BAG-1004", "O-", -10, "expired", "North Branch", 350),
    ("BAG-1005", "O+", 2, "available", "Central Blood Bank", 450),
    ("BAG-1006", "O+", 6, "available", "City Blood Bank", 450),
    ("BAG-1007", "O+", 15, "available", "North Branch", 450),
    ("BAG-1008", "A+", 5, "available", "Central Blood Bank", 450),
    ("BAG-1009", "A+", 5, "available", "City Blood Bank", 450),        # same expiry as BAG-1008 (tie-break test)
    ("BAG-1010", "A+", 18, "available", "North Branch", 350),
    ("BAG-1011", "B+", 7, "available", "Central Blood Bank", 450),
    ("BAG-1012", "B+", 11, "available", "City Blood Bank", 450),
    ("BAG-1013", "AB+", 13, "available", "Central Blood Bank", 450),
    ("BAG-1014", "AB-", 20, "dispatched", "North Branch", 450),        # used by the historic dispatch
    ("BAG-1015", "A-", 25, "discarded", "City Blood Bank", 450),
    ("BAG-1016", "O+", 25, "available", "Central Blood Bank", 450),
]

# (request_id, hospital, group, units, units_allocated, urgency, status, notes)
REQUESTS = [
    ("REQ-0001", "Lakeside Hospital", "AB-", 1, 1, 2, "fulfilled", "Scheduled surgery (completed earlier)"),
    ("REQ-0002", "City General Hospital", "A+", 3, 0, 3, "pending", "Routine ward stock"),
    ("REQ-0003", "Metro Trauma Center", "O-", 2, 0, 1, "pending", "Trauma bay - demo request"),
    ("REQ-0004", "St. Mary Surgical Institute", "B+", 8, 0, 2, "pending", "Planned surgeries this week"),
    ("REQ-0005", "Riverside Clinic", "AB-", 2, 0, 2, "pending", "No compatible stock in this demo"),
    ("REQ-0006", "Northside Community Hospital", "AB+", 2, 0, 3, "pending", None),
    ("REQ-0007", "Eastside Emergency Unit", "A+", 1, 0, 1, "pending", "Emergency - demo request"),
]


def seed_demo_data(db: Session, today: date = None):
    today = today or date.today()
    now = datetime.now()

    for key, value in DEFAULT_SETTINGS.items():
        db.add(AppSetting(key=key, value=value))

    bag_rows = {}
    for bag_id, group, days, status, location, volume in BAGS:
        expiry = today + timedelta(days=days)
        row = BloodBag(
            bag_id=bag_id, blood_group=group, collection_date=expiry - timedelta(days=42),
            expiry_date=expiry, volume_ml=volume, location=location, status=status,
            created_at=now - timedelta(days=3),
        )
        db.add(row)
        bag_rows[bag_id] = row

    request_rows = {}
    for seq, (request_id, hospital, group, units, allocated, urgency, status, notes) in enumerate(REQUESTS, start=1):
        row = HospitalRequest(
            request_id=request_id, hospital_name=hospital, required_blood_group=group,
            units_needed=units, units_allocated=allocated, urgency_level=urgency,
            arrival_sequence=seq, status=status, notes=notes,
            created_at=now - timedelta(minutes=(len(REQUESTS) - seq + 1) * 7) - (timedelta(days=2) if seq == 1 else timedelta()),
        )
        db.add(row)
        request_rows[request_id] = row
    db.flush()

    # one historic dispatch so the history page is not empty on first start
    bag = bag_rows["BAG-1014"]
    dispatch = Dispatch(
        request_pk=request_rows["REQ-0001"].id,
        processed_at=now - timedelta(days=2),
        units_allocated=1, units_remaining=0, result="fulfilled", groups_considered="AB-,A-,B-,O-",
        decision_summary=(
            "REQ-0001 (Lakeside Hospital) was at the root of the priority heap: urgency 2 (Surgery) is the "
            "most urgent level waiting. Requested group AB-; donor groups considered (simplified educational "
            f"table): AB-, A-, B-, O-. Bags chosen by FEFO (earliest expiry first): BAG-1014 (AB-, expires "
            f"{bag.expiry_date.isoformat()}). Request fully fulfilled."
        ),
    )
    db.add(dispatch)
    db.flush()
    db.add(DispatchItem(
        dispatch_id=dispatch.id, blood_bag_pk=bag.id, donor_blood_group="AB-",
        expiry_date_at_dispatch=bag.expiry_date,
    ))
    db.commit()


def seed_if_empty(db: Session):
    has_data = db.scalar(select(func.count(BloodBag.id))) or db.scalar(select(func.count(HospitalRequest.id)))
    if not has_data:
        seed_demo_data(db)
        return True
    return False


def reset_demo_data(db: Session):
    """Delete every row (children first because of foreign keys), then seed again."""
    for model in (DispatchItem, Dispatch, HospitalRequest, BloodBag, AppSetting):
        db.execute(delete(model))
    db.commit()
    seed_demo_data(db)
    return {
        "bags": db.scalar(select(func.count(BloodBag.id))),
        "requests": db.scalar(select(func.count(HospitalRequest.id))),
        "dispatches": db.scalar(select(func.count(Dispatch.id))),
    }
