from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.product_image import ProductImage
    from app.models.product_variant import ProductVariant


class Product(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """A furniture or decor product available in the catalogue."""

    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint(
            "base_price_paise >= 0",
            name="base_price_non_negative",
        ),
    )

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "collections.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(220),
        nullable=False,
        unique=True,
        index=True,
    )

    short_description: Mapped[str] = mapped_column(
        String(400),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    base_price_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    material: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
    )

    colour: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    style: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    collection: Mapped[Collection] = relationship(
        back_populates="products",
    )

    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductImage.display_order",
    )

    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
