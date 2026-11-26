from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PackageInput(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    duration_days: int = Field(ge=1, le=365)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    capacity: int = Field(ge=0)
    start_date: date
    active: bool = True

    @field_validator("start_date")
    @classmethod
    def future_date(cls, value):
        if value <= date.today():
            raise ValueError("Departure date must be in the future")
        return value


class PackageResponse(PackageInput):
    model_config = ConfigDict(from_attributes=True)
    id: int

    # Existing trips can become historical after their creation.
    @field_validator("start_date")
    @classmethod
    def future_date(cls, value):
        return value


class BookingLineInput(BaseModel):
    item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=10)
    expected_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    expected_start_date: date | None = None


class BookingInput(BaseModel):
    lines: list[BookingLineInput] = Field(min_length=1, max_length=20)

    @field_validator("lines")
    @classmethod
    def unique_items(cls, lines):
        if len({line.item_id for line in lines}) != len(lines):
            raise ValueError("Each package may appear only once")
        return lines


class LineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item_id: int
    quantity: int
    unit_price: Decimal


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    total: Decimal
    refund: Decimal | None
    lines: list[LineResponse]


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ConfirmInput(BaseModel):
    confirm: bool


class StatusInput(BaseModel):
    status: Annotated[str, Field(pattern="^(COMPLETED)$")]
