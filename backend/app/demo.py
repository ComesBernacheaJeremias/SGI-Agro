"""Datos de ejemplo para mostrar el sistema (nunca en producción).

Arma una temporada creíble con los servicios reales (mismas reglas que la pantalla):
establecimiento con dos lotes, tomate en invernadero y manzana a campo, compras de insumos,
labores con maquinaria, cosecha, ventas, cobros, pagos, gastos de caja, reventa y un plan de
mantenimiento. Las fechas son relativas a hoy.

Uso: docker compose exec api python -m app.cli seed-demo
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.assets.maintenance_router import PlanService, ReadingService
from app.modules.assets.models import AssetKind, AssetMeter
from app.modules.assets.router import AssetCreate, AssetService
from app.modules.assets.schemas import PlanCreate, ReadingCreate
from app.modules.commercial.cash_service import CashMovementService
from app.modules.commercial.document_service import CommercialDocumentService
from app.modules.commercial.models import (
    CashAccountKind,
    CashMovementKind,
    Direction,
    ExpenseCategory,
    LineKind,
    PaymentMethod,
)
from app.modules.commercial.payment_service import PaymentService
from app.modules.commercial.router import CashAccountService
from app.modules.commercial.schemas import (
    AllocationIn,
    CashAccountIn,
    CashMovementIn,
    CommercialDocumentIn,
    CommercialLineIn,
    PaymentIn,
    PaymentLineIn,
)
from app.modules.masterdata.models import (
    Product,
    ProductType,
    Unit,
    VatCondition,
    WarehouseKind,
)
from app.modules.masterdata.schemas import (
    ConversionIn,
    PartyCreate,
    ProductCreate,
    WarehouseCreate,
)
from app.modules.masterdata.service import PartyService, ProductService, WarehouseService
from app.modules.production.catalog import (
    CropCreate,
    CropService,
    FarmCreate,
    FarmService,
    PlotCreate,
    PlotService,
)
from app.modules.production.models import CropKind, OperationType, PlotKind
from app.modules.production.schemas import (
    AssetUseIn,
    CycleCreate,
    CycleShareIn,
    HarvestIn,
    InputIn,
    OperationIn,
)
from app.modules.production.service import CycleService, FieldOperationService

TODAY = date.today()
D = Decimal


def ago(days: int) -> date:
    return TODAY - timedelta(days=days)


class Demo:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.units = {u.code: u.id for u in session.scalars(select(Unit))}
        self.types = {t.name: t.id for t in session.scalars(select(OperationType))}
        self.categories = {c.name: c.id for c in session.scalars(select(ExpenseCategory))}

    def product(self, name: str, type_: ProductType, unit: str, **extra: object) -> UUID:
        data = ProductCreate(name=name, type=type_, unit_id=self.units[unit], **extra)
        return ProductService(self.s).create(data).id

    def document(self, **body: object) -> UUID:
        data = CommercialDocumentIn.model_validate(body)
        return CommercialDocumentService(self.s).create(data)[0].id

    def run(self) -> None:
        s = self.s
        galpon = (
            WarehouseService(s)
            .create(WarehouseCreate(name="Galpón central", kind=WarehouseKind.SHED))
            .id
        )
        quimicos = (
            WarehouseService(s)
            .create(
                WarehouseCreate(name="Depósito de agroquímicos", kind=WarehouseKind.AGROCHEMICALS)
            )
            .id
        )

        glifosato = self.product("Glifosato 48 %", ProductType.INPUT, "L", min_stock=D(20))
        npk = self.product("Fertilizante NPK 15-15-15", ProductType.INPUT, "kg")
        insecticida = self.product("Insecticida piretroide", ProductType.INPUT, "L", min_stock=D(5))
        tomate = self.product(
            "Tomate perita",
            ProductType.OWN_PRODUCE,
            "cajón",
            conversions=[ConversionIn(unit_id=self.units["kg"], quantity=D(18))],
        )
        manzana = self.product("Manzana roja", ProductType.OWN_PRODUCE, "kg")
        bolsas = self.product("Bolsas de rafia", ProductType.RESALE, "un", vat_rate=D(21))

        proveedor = PartyService(s).create(
            PartyCreate(
                name="Agroinsumos del Valle SA",
                cuit="30-71234567-1",
                vat_condition=VatCondition.REGISTERED,
                is_supplier=True,
                payment_days=30,
            )
        )
        mercado = PartyService(s).create(
            PartyCreate(
                name="Mercado Central · Puesto 12",
                vat_condition=VatCondition.REGISTERED,
                is_customer=True,
                payment_days=15,
            )
        )
        verduleria = PartyService(s).create(
            PartyCreate(
                name="Verdulería Don José", vat_condition=VatCondition.MONOTAX, is_customer=True
            )
        )

        campo = (
            FarmService(s)
            .create(FarmCreate(name="La Esperanza", location="Valle Medio", area_ha=D(12)))
            .id
        )
        lote1 = (
            PlotService(s)
            .create(
                PlotCreate(farm_id=campo, name="Lote 1", area_ha=D(5), kind=PlotKind.OPEN_FIELD)
            )
            .id
        )
        invernadero = (
            PlotService(s)
            .create(
                PlotCreate(
                    farm_id=campo, name="Invernadero 1", area_ha=D(1), kind=PlotKind.GREENHOUSE
                )
            )
            .id
        )
        cultivo_tomate = (
            CropService(s)
            .create(
                CropCreate(
                    species="Tomate",
                    variety="Perita",
                    kind=CropKind.VEGETABLE,
                    harvest_product_id=tomate,
                )
            )
            .id
        )
        cultivo_manzana = (
            CropService(s)
            .create(
                CropCreate(
                    species="Manzana",
                    variety="Red Delicious",
                    kind=CropKind.FRUIT,
                    harvest_product_id=manzana,
                )
            )
            .id
        )

        tractor = (
            AssetService(s)
            .create(
                AssetCreate(
                    name="Tractor John Deere 5075",
                    kind=AssetKind.MACHINERY,
                    meter=AssetMeter.HOURS,
                    rate=D(9000),
                )
            )
            .id
        )
        camioneta = (
            AssetService(s)
            .create(
                AssetCreate(
                    name="Camioneta Hilux", kind=AssetKind.VEHICLE, meter=AssetMeter.KM, rate=D(350)
                )
            )
            .id
        )
        ReadingService(s).create(ReadingCreate(asset_id=tractor, date=ago(100), value=D(2340)))
        PlanService(s).create(
            PlanCreate(
                asset_id=tractor,
                name="Cambio de aceite y filtros",
                every_usage=D(250),
                every_months=6,
                start_date=ago(100),
                start_reading=D(2130),
            )
        )

        caja = (
            CashAccountService(s)
            .create(
                CashAccountIn(
                    name="Caja",
                    kind=CashAccountKind.CASH,
                    opening_balance=D(800000),
                    opening_date=ago(120),
                )
            )
            .id
        )
        banco = (
            CashAccountService(s)
            .create(
                CashAccountIn(
                    name="Banco Nación c/c",
                    kind=CashAccountKind.BANK,
                    opening_balance=D(4500000),
                    opening_date=ago(120),
                )
            )
            .id
        )

        # Compra de insumos y mercadería de reventa
        compra = self.document(
            direction=Direction.PURCHASE,
            party_id=proveedor.id,
            date=ago(95),
            letter="A",
            pos_number="7",
            number="10231",
            warehouse_id=quimicos,
            lines=[
                CommercialLineIn(
                    kind=LineKind.PRODUCT,
                    product_id=glifosato,
                    unit_id=self.units["L"],
                    quantity=D(60),
                    unit_price=D(6200),
                ),
                CommercialLineIn(
                    kind=LineKind.PRODUCT,
                    product_id=npk,
                    unit_id=self.units["kg"],
                    quantity=D(800),
                    unit_price=D(950),
                ),
                CommercialLineIn(
                    kind=LineKind.PRODUCT,
                    product_id=insecticida,
                    unit_id=self.units["L"],
                    quantity=D(12),
                    unit_price=D(18500),
                ),
            ],
        )
        self.document(
            direction=Direction.PURCHASE,
            party_id=proveedor.id,
            date=ago(80),
            letter="A",
            pos_number="7",
            number="10302",
            warehouse_id=galpon,
            lines=[
                CommercialLineIn(
                    kind=LineKind.PRODUCT,
                    product_id=bolsas,
                    unit_id=self.units["un"],
                    quantity=D(500),
                    unit_price=D(420),
                )
            ],
        )

        # Ciclos, labores y cosecha
        cycles = CycleService(s)
        ciclo_tomate = cycles.create(
            CycleCreate(
                plot_id=invernadero, crop_id=cultivo_tomate, area_ha=D(1), start_date=ago(110)
            )
        ).id
        ciclo_manzana = cycles.create(
            CycleCreate(plot_id=lote1, crop_id=cultivo_manzana, area_ha=D(5), start_date=ago(115))
        ).id
        ops = FieldOperationService(s)

        def labor(days: int, tipo: str, cycle: UUID, **extra: object) -> None:
            ops.create(
                OperationIn(
                    date=ago(days),
                    operation_type_id=self.types[tipo],
                    cycles=[CycleShareIn(crop_cycle_id=cycle)],
                    **extra,
                )
            )

        labor(
            90,
            "Preparación de suelo",
            ciclo_tomate,
            assets=[AssetUseIn(asset_id=tractor, usage=D(3))],
        )
        labor(
            85,
            "Fertilización",
            ciclo_tomate,
            inputs=[
                InputIn(
                    product_id=npk,
                    unit_id=self.units["kg"],
                    warehouse_id=quimicos,
                    dose_per_ha=D(250),
                )
            ],
        )
        labor(
            60,
            "Aplicación",
            ciclo_tomate,
            inputs=[
                InputIn(
                    product_id=insecticida,
                    unit_id=self.units["L"],
                    warehouse_id=quimicos,
                    quantity=D(3),
                )
            ],
            assets=[AssetUseIn(asset_id=tractor, usage=D(2))],
        )
        labor(
            88,
            "Desmalezado",
            ciclo_manzana,
            inputs=[
                InputIn(
                    product_id=glifosato,
                    unit_id=self.units["L"],
                    warehouse_id=quimicos,
                    dose_per_ha=D(4),
                )
            ],
            assets=[AssetUseIn(asset_id=tractor, usage=D(8))],
        )
        labor(
            70,
            "Fertilización",
            ciclo_manzana,
            inputs=[
                InputIn(
                    product_id=npk,
                    unit_id=self.units["kg"],
                    warehouse_id=quimicos,
                    dose_per_ha=D(80),
                )
            ],
            assets=[AssetUseIn(asset_id=tractor, usage=D(6))],
        )
        labor(40, "Poda", ciclo_manzana, assets=[AssetUseIn(asset_id=camioneta, usage=D(120))])
        labor(
            30,
            "Cosecha",
            ciclo_tomate,
            harvest=HarvestIn(unit_id=self.units["cajón"], quantity=D(420), warehouse_id=galpon),
        )
        labor(
            15,
            "Cosecha",
            ciclo_tomate,
            harvest=HarvestIn(unit_id=self.units["cajón"], quantity=D(380), warehouse_id=galpon),
        )

        # Servicio contratado con destino al ciclo de tomate
        self.document(
            direction=Direction.PURCHASE,
            party_id=proveedor.id,
            date=ago(55),
            has_invoice=False,
            lines=[
                CommercialLineIn(
                    kind=LineKind.EXPENSE,
                    expense_category_id=self.categories["Servicios contratados"],
                    description="Colocación de riego por goteo",
                    unit_price=D(380000),
                    crop_cycle_id=ciclo_tomate,
                )
            ],
        )

        # Ventas y cobros
        venta1 = self.document(
            direction=Direction.SALE,
            party_id=mercado.id,
            date=ago(25),
            letter="A",
            pos_number="3",
            number="1540",
            warehouse_id=galpon,
            lines=[
                CommercialLineIn(
                    kind=LineKind.PRODUCT,
                    product_id=tomate,
                    unit_id=self.units["cajón"],
                    quantity=D(350),
                    unit_price=D(14500),
                    vat_rate=D("10.5"),
                )
            ],
        )
        self.document(
            direction=Direction.SALE,
            party_id=verduleria.id,
            date=ago(10),
            has_invoice=False,
            warehouse_id=galpon,
            lines=[
                CommercialLineIn(
                    kind=LineKind.PRODUCT,
                    product_id=tomate,
                    unit_id=self.units["cajón"],
                    quantity=D(120),
                    unit_price=D(15500),
                    vat_rate=D(0),
                ),
                CommercialLineIn(
                    kind=LineKind.PRODUCT,
                    product_id=bolsas,
                    unit_id=self.units["un"],
                    quantity=D(200),
                    unit_price=D(900),
                    vat_rate=D(0),
                ),
            ],
        )
        PaymentService(s).create(
            PaymentIn(
                direction=Direction.SALE,
                party_id=mercado.id,
                date=ago(12),
                lines=[
                    PaymentLineIn(
                        method=PaymentMethod.TRANSFER,
                        cash_account_id=banco,
                        amount=D(3000000),
                        reference="Transf. 88213",
                    )
                ],
                allocations=[AllocationIn(document_id=venta1, amount=D(3000000))],
            )
        )
        PaymentService(s).create(
            PaymentIn(
                direction=Direction.PURCHASE,
                party_id=proveedor.id,
                date=ago(60),
                lines=[
                    PaymentLineIn(
                        method=PaymentMethod.TRANSFER, cash_account_id=banco, amount=D(1500000)
                    )
                ],
                allocations=[AllocationIn(document_id=compra, amount=D(1500000))],
            )
        )

        # Gastos de caja: combustible del tractor y un gasto de estructura
        movements = CashMovementService(s)
        movements.create(
            CashMovementIn(
                date=ago(45),
                kind=CashMovementKind.EXPENSE,
                cash_account_id=caja,
                amount=D(185000),
                description="Gasoil",
                expense_category_id=self.categories["Combustible"],
                asset_id=tractor,
            )
        )
        movements.create(
            CashMovementIn(
                date=ago(20),
                kind=CashMovementKind.EXPENSE,
                cash_account_id=banco,
                amount=D(96000),
                description="Seguro integral",
                expense_category_id=self.categories["Seguros"],
            )
        )
        movements.create(
            CashMovementIn(
                date=ago(5),
                kind=CashMovementKind.WITHDRAWAL,
                cash_account_id=caja,
                amount=D(250000),
                description="Retiro del dueño",
            )
        )
        s.flush()


def has_data(session: Session) -> bool:
    return session.scalar(select(Product.id).limit(1)) is not None


def seed_demo(session: Session) -> None:
    Demo(session).run()
