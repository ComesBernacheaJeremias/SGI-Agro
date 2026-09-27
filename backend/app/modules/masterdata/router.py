from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.crud_router import CrudPermissions, crud_router
from app.modules.identity.dependencies import CurrentUser
from app.modules.masterdata.models import (
    PRODUCT_TYPE_LABELS,
    UNIT_KIND_LABELS,
    VAT_CONDITION_LABELS,
    WAREHOUSE_KIND_LABELS,
    ProductType,
)
from app.modules.masterdata.permissions import (
    MASTERDATA_DEACTIVATE,
    MASTERDATA_READ,
    MASTERDATA_WRITE,
)
from app.modules.masterdata.schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    MasterdataOptions,
    Option,
    PartyCreate,
    PartyOut,
    PartyUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    UnitCreate,
    UnitOut,
    UnitUpdate,
    WarehouseCreate,
    WarehouseOut,
    WarehouseUpdate,
)
from app.modules.masterdata.service import (
    CategoryService,
    PartyService,
    ProductService,
    UnitService,
    WarehouseService,
)

PERMISSIONS = CrudPermissions(
    read=MASTERDATA_READ, write=MASTERDATA_WRITE, deactivate=MASTERDATA_DEACTIVATE
)

VAT_RATES = [
    Decimal("0"),
    Decimal("2.5"),
    Decimal("5"),
    Decimal("10.5"),
    Decimal("21"),
    Decimal("27"),
]


def _product_filters(
    type: Annotated[ProductType | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
) -> dict[str, Any]:
    return {"type": type, "category_id": category_id}


def _party_filters(
    role: Annotated[Literal["customer", "supplier"] | None, Query()] = None,
) -> dict[str, Any]:
    return {"role": role}


def _options(labels: dict[Any, str]) -> list[Option]:
    return [Option(value=str(value), label=label) for value, label in labels.items()]


options_router = APIRouter(prefix="/api/v1/masterdata", tags=["masterdata"])


@options_router.get("/options")
def masterdata_options(_: CurrentUser) -> MasterdataOptions:
    return MasterdataOptions(
        product_types=_options(PRODUCT_TYPE_LABELS),
        unit_kinds=_options(UNIT_KIND_LABELS),
        vat_conditions=_options(VAT_CONDITION_LABELS),
        warehouse_kinds=_options(WAREHOUSE_KIND_LABELS),
        vat_rates=VAT_RATES,
    )


routers = [
    options_router,
    crud_router(
        prefix="/api/v1/units",
        tag="units",
        service=UnitService,
        out=UnitOut,
        create=UnitCreate,
        update=UnitUpdate,
        permissions=PERMISSIONS,
    ),
    crud_router(
        prefix="/api/v1/product-categories",
        tag="product-categories",
        service=CategoryService,
        out=CategoryOut,
        create=CategoryCreate,
        update=CategoryUpdate,
        permissions=PERMISSIONS,
    ),
    crud_router(
        prefix="/api/v1/products",
        tag="products",
        service=ProductService,
        out=ProductOut,
        create=ProductCreate,
        update=ProductUpdate,
        filters=_product_filters,
        permissions=PERMISSIONS,
    ),
    crud_router(
        prefix="/api/v1/parties",
        tag="parties",
        service=PartyService,
        out=PartyOut,
        create=PartyCreate,
        update=PartyUpdate,
        filters=_party_filters,
        permissions=PERMISSIONS,
    ),
    crud_router(
        prefix="/api/v1/warehouses",
        tag="warehouses",
        service=WarehouseService,
        out=WarehouseOut,
        create=WarehouseCreate,
        update=WarehouseUpdate,
        permissions=PERMISSIONS,
    ),
]
