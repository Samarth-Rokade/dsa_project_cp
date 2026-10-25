"""
Blood-group compatibility lookup  -  SIMPLIFIED EDUCATIONAL TABLE.

!! This is a teaching table for a data-structures project. It is NOT clinical guidance and
!! must never be used for real transfusion decisions (real practice needs cross-matching,
!! antibody screening and hospital protocols).

Direction (important):
    row    = RECIPIENT  = the blood group the hospital REQUESTED
    column = DONOR      = the blood group of the STOCK that may be used
    RECIPIENT_TO_DONORS["AB+"] -> every donor group the simulation allows for an AB+ request.

The table is stored as a plain dictionary of lists and ALSO as an 8x8 two-dimensional array
(COMPATIBILITY_MATRIX[recipient_index][donor_index] = 1 or 0) - a natural use of a 2-D array.
Compatibility is always looked up in the table, never guessed from the text of the group name.

Two modes (configurable in Settings):
    "educational" -> use the table below
    "exact"       -> only the identical group is eligible (safest fallback)
"""
from ..constants import BLOOD_GROUPS

RECIPIENT_TO_DONORS = {
    "O-":  ["O-"],
    "O+":  ["O+", "O-"],
    "A-":  ["A-", "O-"],
    "A+":  ["A+", "A-", "O+", "O-"],
    "B-":  ["B-", "O-"],
    "B+":  ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
}

# 2-D array view: rows = recipient, columns = donor (both in BLOOD_GROUPS order)
COMPATIBILITY_MATRIX = [
    [1 if donor in RECIPIENT_TO_DONORS[recipient] else 0 for donor in BLOOD_GROUPS]
    for recipient in BLOOD_GROUPS
]


def get_compatible_donor_groups(requested_group, mode="educational"):
    """Donor stock groups the simulation allows for a request of `requested_group`."""
    if requested_group not in BLOOD_GROUPS:
        raise ValueError(f"Unknown blood group: {requested_group!r}")
    if mode == "exact":
        return [requested_group]
    # read the row of the matrix for this recipient
    row = COMPATIBILITY_MATRIX[BLOOD_GROUPS.index(requested_group)]
    return [donor for donor, allowed in zip(BLOOD_GROUPS, row) if allowed]


def matrix_for_display(mode="educational"):
    rows = []
    for recipient in BLOOD_GROUPS:
        allowed = get_compatible_donor_groups(recipient, mode)
        rows.append({"recipient": recipient, "cells": [g in allowed for g in BLOOD_GROUPS]})
    return {"groups": BLOOD_GROUPS, "rows": rows, "mode": mode}
