import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# from app.models.inventory import Inventory
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant


class ProductRepository:
    """Database operations for products and their nested records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Why: The repository receives the request’s database session so all operations can be part of one transaction.

    @staticmethod
    def detail_query() -> Select[tuple[Product]]:
        """Create a query that loads complete product relationships."""

        return select(Product).options(
            selectinload(Product.images),
            selectinload(Product.variants).selectinload(ProductVariant.inventory),
        )

    # Without eager loading, accessing:

    # product.images
    # product.variants
    # variant.inventory

    # could trigger additional database queries later.

    async def create(
        self,
        *,
        product: Product,
        images: list[ProductImage],
        variants: list[ProductVariant],
    ) -> Product:
        """Add a product and all nested records to the transaction."""

        product.images.extend(images)
        product.variants.extend(variants)

        self.session.add(product)

        await self.session.flush()

        self.session.expire(
            product,
            attribute_names=[
                "images",
                "variants",
            ],
        )

        created_product = await self.get_by_id(
            product.id,
            include_details=True,
        )

        if created_product is None:
            raise RuntimeError("Product could not be reloaded after creation.")

        return created_product

    async def get_by_id(
        self,
        product_id: uuid.UUID,
        *,
        include_details: bool = False,
    ) -> Product | None:
        """Find a product using its UUID."""

        if include_details:
            query = self.detail_query().where(
                Product.id == product_id,
            )
        else:
            query = select(Product).where(
                Product.id == product_id,
            )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_by_slug(
        self,
        slug: str,
        *,
        include_details: bool = False,
    ) -> Product | None:
        """Find a product using its URL slug."""

        if include_details:
            query = self.detail_query().where(
                Product.slug == slug,
            )
        else:
            query = select(Product).where(
                Product.slug == slug,
            )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        name: str,
    ) -> Product | None:
        """Find a product using a case-insensitive name."""

        query = select(Product).where(
            func.lower(Product.name) == name.lower(),
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def collection_exists(
        self,
        collection_id: uuid.UUID,
    ) -> bool:
        """Check whether the selected collection exists."""

        from app.models.collection import Collection

        query = select(select(Collection.id).where(Collection.id == collection_id).exists())

        result = await self.session.execute(query)

        return bool(result.scalar())

    async def find_existing_skus(
        self,
        skus: Sequence[str],
    ) -> set[str]:
        """Return supplied SKUs that already exist in PostgreSQL."""

        if not skus:
            return set()

        normalized_skus = {sku.upper() for sku in skus}

        query = select(ProductVariant.sku).where(
            ProductVariant.sku.in_(normalized_skus),
        )

        result = await self.session.execute(query)

        return set(result.scalars().all())

    async def list(
        self,
        *,
        offset: int,
        limit: int,
        active_only: bool,
        collection_id: uuid.UUID | None = None,
        material: str | None = None,
        colour: str | None = None,
        style: str | None = None,
        featured_only: bool = False,
        search: str | None = None,
    ) -> Sequence[Product]:
        """Return filtered products for cards and search results."""

        query = select(Product)

        if active_only:
            query = query.where(
                Product.is_active.is_(True),
            )

        if collection_id is not None:
            query = query.where(
                Product.collection_id == collection_id,
            )

        if material is not None:
            query = query.where(
                func.lower(Product.material) == material.lower(),
            )

        if colour is not None:
            query = query.where(
                func.lower(Product.colour) == colour.lower(),
            )

        if style is not None:
            query = query.where(
                func.lower(Product.style) == style.lower(),
            )

        if featured_only:
            query = query.where(
                Product.is_featured.is_(True),
            )

        if search:
            cleaned_search = search.strip()

            if cleaned_search:
                search_pattern = f"%{cleaned_search}%"

                query = query.where(
                    or_(
                        Product.name.ilike(search_pattern),
                        Product.short_description.ilike(search_pattern),
                        Product.material.ilike(search_pattern),
                        Product.colour.ilike(search_pattern),
                        Product.style.ilike(search_pattern),
                    )
                )

        query = (
            query.order_by(
                Product.is_featured.desc(),
                Product.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)

        return result.scalars().all()

    async def count(
        self,
        *,
        active_only: bool,
        collection_id: uuid.UUID | None = None,
    ) -> int:
        """Count products matching common catalogue filters."""

        query = select(func.count(Product.id))

        if active_only:
            query = query.where(
                Product.is_active.is_(True),
            )

        if collection_id is not None:
            query = query.where(
                Product.collection_id == collection_id,
            )

        result = await self.session.execute(query)

        return int(result.scalar_one())

    async def reload_details(
        self,
        product_id: uuid.UUID,
    ) -> Product | None:
        """Reload complete product data from PostgreSQL."""

        existing_product = await self.get_by_id(product_id)

        if existing_product is not None:
            self.session.expire(
                existing_product,
                attribute_names=[
                    "images",
                    "variants",
                ],
            )

        return await self.get_by_id(
            product_id,
            include_details=True,
        )

    async def delete(
        self,
        product: Product,
    ) -> None:
        """Mark a product for permanent deletion."""

        await self.session.delete(product)
