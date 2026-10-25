"""Pydantic models: validate everything that comes IN to the API."""
import re
from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

BloodGroup = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
BAG_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{3,20}$")


class BagCreate(BaseModel):
    bag_id: Optional[str] = None                     # blank -> generated (BAG-1001, ...)
    blood_group: BloodGroup
    collection_date: date
    expiry_date: date
    volume_ml: Optional[int] = Field(default=450, ge=50, le=1000)
    location: str = Field(default="Central Blood Bank", min_length=1, max_length=60)

    @field_validator("bag_id")
    @classmethod
    def check_bag_id(cls, v):
        if v is None or not v.strip():
            return None
        v = v.strip().upper()
        if not BAG_ID_PATTERN.match(v):
            raise ValueError("Bag ID must be 3-20 characters: letters, digits and dashes only")
        return v

    @field_validator("location")
    @classmethod
    def strip_location(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Location is required")
        return v

    @model_validator(mode="after")
    def expiry_after_collection(self):
        if self.expiry_date <= self.collection_date:
            raise ValueError("Expiry date must be later than the collection date")
        return self


class BagUpdate(BaseModel):
    collection_date: Optional[date] = None
    expiry_date: Optional[date] = None
    volume_ml: Optional[int] = Field(default=None, ge=50, le=1000)
    location: Optional[str] = Field(default=None, min_length=1, max_length=60)
    status: Optional[Literal["available", "reserved", "discarded"]] = None


class RequestCreate(BaseModel):
    hospital_name: str = Field(min_length=2, max_length=80)
    required_blood_group: BloodGroup
    units_needed: int = Field(gt=0, le=50)
    urgency_level: Literal[1, 2, 3]
    notes: Optional[str] = Field(default=None, max_length=200)

    @field_validator("hospital_name")
    @classmethod
    def strip_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Hospital name must be at least 2 characters")
        return v


class SettingsUpdate(BaseModel):
    expiring_soon_days: Optional[int] = Field(default=None, ge=1, le=60)
    compatibility_mode: Optional[Literal["educational", "exact"]] = None


# ---------- DSA Lab inputs ----------
class HeapOp(BaseModel):
    op: Literal["insert", "extract"]
    label: Optional[str] = Field(default=None, max_length=20)
    urgency_level: Optional[Literal[1, 2, 3]] = None


class HeapDemoIn(BaseModel):
    operations: List[HeapOp] = Field(max_length=60)


class SortDemoIn(BaseModel):
    source: Literal["inventory", "sample"] = "inventory"
    algorithm: Literal["merge", "quick"] = "merge"
    sort_by: Literal["expiry_date", "collection_date", "blood_group", "bag_id"] = "expiry_date"
    order: Literal["asc", "desc"] = "asc"
    sample: Optional[List[int]] = Field(default=None, max_length=200)


class SearchDemoIn(BaseModel):
    method: Literal["linear", "binary", "hash"]
    bag_id: str = Field(min_length=1, max_length=20)


class HashDemoIn(BaseModel):
    keys: List[str] = Field(max_length=30)
    capacity: int = Field(default=7, ge=3, le=31)
    lookup: Optional[str] = Field(default=None, max_length=30)
