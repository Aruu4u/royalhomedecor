import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from app.core.auth import AdminUserDependency
from app.schemas.product import (
    ProductCreate,
    ProductDetailResponse,
    ProductSummaryResponse,
    ProductUpdate,
)
from app.services.dependencies import ProductServiceDependency


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product with images, variants, and inventory",
)
async def create_product(
    data: ProductCreate, service: ProductServiceDependency, admin: AdminUserDependency
) -> ProductDetailResponse:
    """Create a complete nested catalogue product."""

    product = await service.create_product(data)

    return ProductDetailResponse.model_validate(product)


@router.get(
    "",
    response_model=list[ProductSummaryResponse],
    summary="List and filter products",
)
async def list_products(
    service: ProductServiceDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    active_only: bool = True,
    collection_id: uuid.UUID | None = None,
    material: str | None = None,
    colour: str | None = None,
    style: str | None = None,
    featured_only: bool = False,
    search: str | None = None,
) -> list[ProductSummaryResponse]:
    """Return products for cards, search, and collection sections."""

    products = await service.list_products(
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

    return [ProductSummaryResponse.model_validate(product) for product in products]


@router.get(
    "/{slug}",
    response_model=ProductDetailResponse,
    summary="Get one product by slug",
)
async def get_product(
    slug: str,
    service: ProductServiceDependency,
) -> ProductDetailResponse:
    """Return complete product details for the product page."""

    product = await service.get_product_by_slug(slug)

    return ProductDetailResponse.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Update a product",
)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    service: ProductServiceDependency,
    admin: AdminUserDependency,
) -> ProductDetailResponse:
    """Partially update a product's main fields."""

    product = await service.update_product(
        product_id,
        data,
    )

    return ProductDetailResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
)
async def delete_product(
    product_id: uuid.UUID, service: ProductServiceDependency, admin: AdminUserDependency
) -> Response:
    """Permanently delete a product and its nested records."""

    await service.delete_product(product_id)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
