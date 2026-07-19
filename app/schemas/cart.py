import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class CartItemCreate(BaseModel):
    """Fields used when adding a variant to the cart."""

    model_config = ConfigDict(extra="forbid")

    variant_id: uuid.UUID

    quantity: int = Field(
        default=1,
        ge=1,
        le=99,
    )


class CartItemUpdate(BaseModel):
    """Fields accepted when changing cart-item quantity."""

    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(
        ge=1,
        le=99,
    )


class CartVariantResponse(BaseModel):
    """Variant information displayed inside the cart."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    name: str
    size_label: str | None
    colour: str | None
    material: str | None
    price_paise: int
    is_active: bool


class CartItemResponse(BaseModel):
    """One populated item returned inside a shopping cart."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    cart_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    variant: CartVariantResponse
    line_total_paise: int
    created_at: datetime
    updated_at: datetime


class CartResponse(BaseModel):
    """Complete customer shopping cart."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    user_id: uuid.UUID
    items: list[CartItemResponse]
    subtotal_paise: int
    total_quantity: int
    created_at: datetime
    updated_at: datetime
