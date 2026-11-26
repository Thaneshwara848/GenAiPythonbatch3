from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class ItemCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    vegetarian: bool
    price: Money
    capacity: int = Field(ge=0)
    active: bool = True


class ItemUpdate(ItemCreate):
    pass


class ItemResponse(ItemCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class OrderLineCreate(BaseModel):
    item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=10)
    expected_unit_price: Money | None = None


class OrderCreate(BaseModel):
    lines: list[OrderLineCreate] = Field(min_length=1, max_length=30)


class OrderLineResponse(BaseModel):
    item_id: int
    quantity: int
    unit_price: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    total: Decimal
    lines: list[OrderLineResponse]
    model_config = ConfigDict(from_attributes=True)


class StatusUpdate(BaseModel):
    status: str


class SessionCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=120)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ConfirmRequest(BaseModel):
    confirm: bool
