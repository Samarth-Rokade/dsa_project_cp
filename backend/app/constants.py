"""Shared constants. Kept in one place so every module agrees on the allowed values."""

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

BAG_STATUSES = ["available", "reserved", "dispatched", "expired", "discarded"]
REQUEST_STATUSES = ["pending", "partially_fulfilled", "fulfilled", "cancelled"]
WAITING_STATUSES = ("pending", "partially_fulfilled")      # requests still in the priority queue

URGENCY_LABELS = {1: "Critical", 2: "Surgery", 3: "Routine"}

COMPATIBILITY_MODES = ("educational", "exact")

DEFAULT_SETTINGS = {
    "expiring_soon_days": "7",
    "compatibility_mode": "educational",
}

DISCLAIMER = (
    "Educational simulation only. Blood-group compatibility uses a simplified teaching table "
    "and must never be used for real transfusion decisions."
)
