import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.repositories.product import ProductRepository
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
)


class ProductService:
    """Business logic for catalogue products."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProductRepository(session)

    async def create_product(
        self,
        data: ProductCreate,
    ) -> Product:
        """Create a product with images, variants and inventory."""

        collection_exists = await self.repository.collection_exists(
            data.collection_id,
        )

        if not collection_exists:
            raise ResourceNotFoundError(f"Collection '{data.collection_id}' was not found.")

        existing_slug = await self.repository.get_by_slug(
            data.slug,
        )

        if existing_slug is not None:
            raise ResourceConflictError(f"A product with slug '{data.slug}' already exists.")

        existing_name = await self.repository.get_by_name(
            data.name,
        )

        if existing_name is not None:
            raise ResourceConflictError(f"A product named '{data.name}' already exists.")

        submitted_skus = [variant.sku for variant in data.variants]

        existing_skus = await self.repository.find_existing_skus(
            submitted_skus,
        )

        if existing_skus:
            formatted_skus = ", ".join(sorted(existing_skus))

            raise ResourceConflictError(f"These SKUs already exist: {formatted_skus}.")

        product_data = data.model_dump(
            exclude={
                "images",
                "variants",
            },
            mode="json",
        )

        product = Product(
            **product_data,
        )

        images = [
            ProductImage(
                **image_data.model_dump(
                    mode="json",
                )
            )
            for image_data in data.images
        ]

        variants: list[ProductVariant] = []

        for variant_data in data.variants:
            inventory_data = variant_data.inventory

            variant_fields = variant_data.model_dump(
                exclude={
                    "inventory",
                },
                mode="json",
            )

            variant = ProductVariant(
                **variant_fields,
            )

            variant.inventory = Inventory(
                **inventory_data.model_dump(
                    mode="json",
                )
            )

            variants.append(variant)

        try:
            created_product = await self.repository.create(
                product=product,
                images=images,
                variants=variants,
            )

            await self.session.commit()

        except IntegrityError as exception:
            await self.session.rollback()

            raise ResourceConflictError(
                "The product conflicts with an existing record."
            ) from exception

        refreshed_product = await self.repository.reload_details(
            created_product.id,
        )

        if refreshed_product is None:
            raise RuntimeError("Product was created but could not be reloaded.")

        return refreshed_product

    async def list_products(
        self,
        *,
        offset: int,
        limit: int,
        active_only: bool,
        collection_id: uuid.UUID | None,
        material: str | None,
        colour: str | None,
        style: str | None,
        featured_only: bool,
        search: str | None,
    ) -> Sequence[Product]:
        """Return products matching catalogue filters."""

        return await self.repository.list(
            offset=offset,
            limit=limit,
            active_only=active_only,
            collection_id=collection_id,
            material=material,
            colour=colour,
            style=style,
            featured_only=featured_only,
            search=search,
        )

    async def get_product_by_slug(
        self,
        slug: str,
    ) -> Product:
        """Return a detailed product using its URL slug."""

        product = await self.repository.get_by_slug(
            slug,
            include_details=True,
        )

        if product is None:
            raise ResourceNotFoundError(f"Product with slug '{slug}' was not found.")

        return product

    async def update_product(
        self,
        product_id: uuid.UUID,
        data: ProductUpdate,
    ) -> Product:
        """Update the supplied main product fields."""

        product = await self.repository.get_by_id(
            product_id,
        )

        if product is None:
            raise ResourceNotFoundError(f"Product '{product_id}' was not found.")

        update_data = data.model_dump(
            exclude_unset=True,
            mode="json",
        )
        new_collection_id = update_data.get("collection_id")

        if new_collection_id is not None and new_collection_id != product.collection_id:
            collection_exists = await self.repository.collection_exists(
                new_collection_id,
            )

            if not collection_exists:
                raise ResourceNotFoundError(f"Collection '{new_collection_id}' was not found.")

        new_slug = update_data.get("slug")

        if new_slug is not None and new_slug != product.slug:
            existing_slug = await self.repository.get_by_slug(
                new_slug,
            )

            if existing_slug is not None:
                raise ResourceConflictError(f"A product with slug '{new_slug}' already exists.")

        new_name = update_data.get("name")

        if new_name is not None and new_name.lower() != product.name.lower():
            existing_name = await self.repository.get_by_name(
                new_name,
            )

            if existing_name is not None:
                raise ResourceConflictError(f"A product named '{new_name}' already exists.")

        for field_name, field_value in update_data.items():
            setattr(
                product,
                field_name,
                field_value,
            )

        try:
            await self.session.commit()
            await self.session.refresh(product)

        except IntegrityError as exception:
            await self.session.rollback()

            raise ResourceConflictError(
                "The updated product conflicts with an existing record."
            ) from exception

        updated_product = await self.repository.reload_details(
            product.id,
        )

        if updated_product is None:
            raise RuntimeError("Product was updated but could not be reloaded.")

        return updated_product

    async def delete_product(
        self,
        product_id: uuid.UUID,
    ) -> None:
        """Permanently delete a product and nested records."""

        product = await self.repository.get_by_id(
            product_id,
        )

        if product is None:
            raise ResourceNotFoundError(f"Product '{product_id}' was not found.")

        await self.repository.delete(product)

        await self.session.commit()
