"""Turn ORM rows into plain dictionaries for JSON responses."""
from .constants import URGENCY_LABELS
from .domain.compatibility import get_compatible_donor_groups


def effective_status(bag, today):
    """A bag whose expiry date has passed is shown as expired even if the row still says 'available'."""
    if bag.status == "available" and bag.expiry_date < today:
        return "expired"
    return bag.status


def bag_out(bag, today):
    return {
        "id": bag.id,
        "bag_id": bag.bag_id,
        "blood_group": bag.blood_group,
        "collection_date": bag.collection_date.isoformat(),
        "expiry_date": bag.expiry_date.isoformat(),
        "volume_ml": bag.volume_ml,
        "location": bag.location,
        "status": bag.status,
        "effective_status": effective_status(bag, today),
        "days_to_expiry": (bag.expiry_date - today).days,
        "created_at": bag.created_at.isoformat(),
        "updated_at": bag.updated_at.isoformat(),
    }


def request_out(req, mode="educational", queue_position=None):
    return {
        "id": req.id,
        "request_id": req.request_id,
        "hospital_name": req.hospital_name,
        "required_blood_group": req.required_blood_group,
        "units_needed": req.units_needed,
        "units_allocated": req.units_allocated,
        "units_remaining": req.units_needed - req.units_allocated,
        "urgency_level": req.urgency_level,
        "urgency_label": URGENCY_LABELS[req.urgency_level],
        "arrival_sequence": req.arrival_sequence,
        "status": req.status,
        "notes": req.notes,
        "compatible_groups": get_compatible_donor_groups(req.required_blood_group, mode),
        "queue_position": queue_position,
        "created_at": req.created_at.isoformat(),
        "updated_at": req.updated_at.isoformat(),
    }


def dispatch_out(d):
    return {
        "id": d.id,
        "request_id": d.request.request_id,
        "hospital_name": d.request.hospital_name,
        "required_blood_group": d.request.required_blood_group,
        "units_requested": d.request.units_needed,
        "urgency_level": d.request.urgency_level,
        "urgency_label": URGENCY_LABELS[d.request.urgency_level],
        "processed_at": d.processed_at.isoformat(),
        "units_allocated": d.units_allocated,
        "units_remaining": d.units_remaining,
        "result": d.result,
        "groups_considered": [g for g in d.groups_considered.split(",") if g],
        "decision_summary": d.decision_summary,
        "bags": [
            {
                "bag_id": item.bag.bag_id,
                "donor_blood_group": item.donor_blood_group,
                "expiry_date": item.expiry_date_at_dispatch.isoformat(),
            }
            for item in d.items
        ],
    }
