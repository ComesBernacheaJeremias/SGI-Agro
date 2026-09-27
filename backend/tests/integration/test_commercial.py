"""Comercial y caja: compras, ventas (por partida), cobros/pagos, cuentas corrientes, caja."""

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.authorization import OWNER, READ_ONLY, STAFF
from app.modules.inventory.models import StockMove
from tests.factories import login_as
from tests.integration.test_production import TODAY, Farm, day


class Shop(Farm):
    """Escenario de producción + proveedor, cliente, caja y banco."""

    def __init__(self, client: TestClient) -> None:
        super().__init__(client)
        self.supplier = self.post(
            "/api/v1/parties",
            name="Agroinsumos SA",
            vat_condition="registered",
            is_supplier=True,
            payment_days=30,
        )["id"]
        self.customer = self.post(
            "/api/v1/parties", name="Verdulería Juan", vat_condition="monotax", is_customer=True
        )["id"]
        self.cash = self.post(
            "/api/v1/cash-accounts",
            name="Caja",
            kind="cash",
            opening_balance="100000",
            opening_date=day(-60),
        )["id"]
        self.bank = self.post(
            "/api/v1/cash-accounts",
            name="Banco Nación",
            kind="bank",
            opening_balance="0",
            opening_date=day(-60),
        )["id"]
        categories = client.get("/api/v1/expense-categories", params={"page_size": 50}).json()
        self.category = {c["name"]: c["id"] for c in categories["items"]}

    def document(self, **body: Any) -> Any:
        return self.c.post("/api/v1/commercial-documents", json=body)

    def purchase(self, lines: list[dict[str, Any]], number: str = "123", **extra: Any) -> Any:
        body = {
            "direction": "purchase",
            "party_id": self.supplier,
            "date": day(-5),
            "letter": "A",
            "pos_number": "3",
            "number": number,
            "warehouse_id": self.warehouse,
            "lines": lines,
        } | extra
        return self.document(**body)

    def buy_poison(self, liters: str = "10", price: str = "2000", **extra: Any) -> Any:
        line = {
            "kind": "product",
            "product_id": self.poison,
            "unit_id": self.unit["L"],
            "quantity": liters,
            "unit_price": price,
        }
        return self.purchase([line], **extra)

    def sale(
        self, boxes: str, price: str = "10000", lines_batch: str | None = None, **extra: Any
    ) -> Any:
        line = {
            "batch_id": lines_batch,
            "kind": "product",
            "product_id": self.tomato,
            "unit_id": self.unit["cajón"],
            "quantity": boxes,
            "unit_price": price,
            "vat_rate": "0",
        }
        body = {
            "direction": "sale",
            "has_invoice": False,
            "party_id": self.customer,
            "date": day(-1),
            "warehouse_id": self.warehouse,
            "lines": [line],
        } | extra
        return self.document(**body)

    def pay(
        self, direction: str, amount: str, allocations: list[dict[str, Any]], **extra: Any
    ) -> Any:
        party = self.customer if direction == "sale" else self.supplier
        body = {
            "direction": direction,
            "party_id": party,
            "date": day(-1),
            "lines": [{"method": "cash", "cash_account_id": self.cash, "amount": amount}],
            "allocations": allocations,
        } | extra
        return self.c.post("/api/v1/payments", json=body)

    def avg_cost(self, product: str) -> Decimal:
        rows = self.c.get("/api/v1/stock", params={"include_zero": True}).json()["items"]
        return next(Decimal(r["avg_cost"]) for r in rows if r["product"]["id"] == product)

    def cash_balance(self, account: str) -> Decimal:
        rows = self.c.get("/api/v1/cash/balances").json()
        return next(Decimal(r["balance"]) for r in rows if r["account"]["id"] == account)


@pytest.fixture
def shop(client: TestClient, db: Session) -> Shop:
    login_as(client, db, OWNER)
    return Shop(client)


def created(response: Any) -> Any:
    assert response.status_code in (200, 201), response.json()
    return response.json()


def error_code(response: Any) -> str:
    assert response.status_code == 409, response.json()
    return response.json()["error"]["code"]  # type: ignore[no-any-return]


# --- Compras ---


def test_purchase_enters_stock_and_computes_totals(shop: Shop) -> None:
    saved = created(shop.buy_poison("10", "2000", other_taxes="500"))
    doc = saved["document"]
    assert doc["internal_number"].startswith("CPR-")
    assert doc["invoice_label"] == "Factura A 00003-00000123"
    assert Decimal(doc["net_total"]) == Decimal("20000")
    assert Decimal(doc["vat_total"]) == Decimal("4200")
    assert Decimal(doc["total"]) == Decimal("24700")
    assert doc["due_date"] == day(25)  # fecha + 30 días de pago del proveedor
    assert shop.stock(shop.poison) == Decimal("20")  # 10 iniciales + 10 comprados
    assert shop.avg_cost(shop.poison) == Decimal("1500")  # (10×1000 + 10×2000) / 20


def test_purchase_credit_note_returns_stock(shop: Shop) -> None:
    created(shop.buy_poison("10", "2000"))
    created(shop.buy_poison("4", "2000", kind="credit_note", number="9"))
    assert shop.stock(shop.poison) == Decimal("16")


def test_duplicate_invoice_is_rejected_per_supplier(shop: Shop) -> None:
    created(shop.buy_poison())
    assert error_code(shop.buy_poison()) == "DUPLICATE"
    other = shop.post(
        "/api/v1/parties", name="Otro proveedor", vat_condition="registered", is_supplier=True
    )["id"]
    created(shop.buy_poison(party_id=other))


def test_party_role_and_invoice_data_are_validated(shop: Shop) -> None:
    assert error_code(shop.buy_poison(party_id=shop.customer)) == "PARTY_ROLE"
    assert error_code(shop.buy_poison(letter="")) == "INVOICE_NUMBER"
    assert error_code(shop.buy_poison(warehouse_id=None)) == "WAREHOUSE_REQUIRED"


def test_editing_purchase_updates_stock(shop: Shop) -> None:
    doc = created(shop.buy_poison("10", "2000"))["document"]
    body = {
        "direction": "purchase",
        "party_id": shop.supplier,
        "date": day(-5),
        "letter": "A",
        "pos_number": "3",
        "number": "123",
        "warehouse_id": shop.warehouse,
        "lines": [
            {
                "kind": "product",
                "product_id": shop.poison,
                "unit_id": shop.unit["L"],
                "quantity": "5",
                "unit_price": "2000",
            }
        ],
    }
    created(shop.c.put(f"/api/v1/commercial-documents/{doc['id']}", json=body))
    assert shop.stock(shop.poison) == Decimal("15")


def test_cancel_purchase_reverts_stock(shop: Shop) -> None:
    doc = created(shop.buy_poison("10", "2000"))["document"]
    cancelled = created(shop.c.post(f"/api/v1/commercial-documents/{doc['id']}/cancel"))
    assert cancelled["document"]["status"] == "cancelled"
    assert shop.stock(shop.poison) == Decimal("10")


# --- Gastos con destino ---


def test_expense_with_cycle_destination_adds_to_cycle_cost(shop: Shop) -> None:
    cycle = shop.cycle()
    line = {
        "kind": "expense",
        "expense_category_id": shop.category["Servicios contratados"],
        "description": "Fumigación aérea",
        "unit_price": "30000",
        "crop_cycle_id": cycle["id"],
    }
    doc = created(shop.purchase([line], warehouse_id=None))["document"]
    assert doc["lines"][0]["destination"]["plot"]["id"] == shop.plot  # se completa hacia arriba
    created(
        shop.c.post(
            "/api/v1/cash/movements",
            json={
                "date": day(-2),
                "kind": "expense",
                "cash_account_id": shop.cash,
                "amount": "5000",
                "expense_category_id": shop.category["Combustible"],
                "crop_cycle_id": cycle["id"],
            },
        )
    )
    summary = shop.get_cycle(cycle["id"])
    assert Decimal(summary["expense_cost"]) == Decimal("35000")  # neto de IVA
    assert Decimal(summary["total_cost"]) == Decimal("35000")


def test_expense_cannot_target_finished_cycle(shop: Shop) -> None:
    cycle = shop.cycle()
    finish = shop.c.post(f"/api/v1/crop-cycles/{cycle['id']}/finish", json={"end_date": day(-1)})
    assert finish.status_code == 200, finish.json()
    line = {
        "kind": "expense",
        "expense_category_id": shop.category["Fletes"],
        "unit_price": "1000",
        "crop_cycle_id": cycle["id"],
    }
    assert shop.purchase([line], warehouse_id=None).status_code == 409


# --- Ventas ---


def test_own_produce_sale_takes_oldest_batches_first(shop: Shop, db: Session) -> None:
    cycle = shop.cycle()
    assert shop.harvest(cycle["id"], "10").status_code == 201
    second = shop.operation(
        [{"crop_cycle_id": cycle["id"]}],
        type_="Cosecha",
        date=day(-3),
        harvest={
            "unit_id": shop.unit["cajón"],
            "quantity": "8",
            "warehouse_id": shop.warehouse,
            "is_final": False,
        },
    )
    assert second.status_code == 201, second.json()
    doc = created(shop.sale("15"))["document"]
    assert doc["internal_number"].startswith("VTA-")
    assert doc["invoice_label"] == doc["internal_number"]  # sin factura: número interno
    moves = db.scalars(
        select(StockMove)
        .where(StockMove.document_id == doc["stock_document_id"])
        .order_by(StockMove.sub_no)
    ).all()
    assert [m.quantity for m in moves] == [Decimal(-10), Decimal(-5)]
    assert all(m.batch_id is not None and m.crop_cycle_id is None for m in moves)
    assert shop.stock(shop.tomato) == Decimal("3")


def test_sale_without_stock_is_rejected(shop: Shop) -> None:
    assert shop.sale("5").status_code == 409


def test_sale_credit_note_returns_stock(shop: Shop) -> None:
    cycle = shop.cycle()
    shop.harvest(cycle["id"], "10")
    created(shop.sale("6"))
    created(shop.sale("2", kind="credit_note"))
    assert shop.stock(shop.tomato) == Decimal("6")


# --- Cobros, pagos y cuentas corrientes ---


def test_partial_payment_leaves_pending_and_advance(shop: Shop) -> None:
    cycle = shop.cycle()
    shop.harvest(cycle["id"], "10")
    doc = created(shop.sale("5"))["document"]  # 5 × 10.000 = 50.000
    payment = created(shop.pay("sale", "60000", [{"document_id": doc["id"], "amount": "50000"}]))
    assert payment["number"].startswith("REC-")
    assert Decimal(payment["unallocated"]) == Decimal("10000")  # anticipo
    detail = shop.c.get(f"/api/v1/commercial-documents/{doc['id']}").json()
    assert Decimal(detail["pending"]) == 0
    balances = shop.c.get("/api/v1/current-accounts", params={"direction": "sale"}).json()
    row = next(b for b in balances if b["party"]["id"] == shop.customer)
    assert Decimal(row["balance"]) == Decimal("-10000")  # saldo a favor del cliente
    assert Decimal(row["advances"]) == Decimal("10000")
    assert shop.cash_balance(shop.cash) == Decimal("160000")


def test_allocation_cannot_exceed_pending(shop: Shop) -> None:
    doc = created(shop.buy_poison("1", "1000"))["document"]  # total 1.210
    response = shop.pay("purchase", "5000", [{"document_id": doc["id"], "amount": "2000"}])
    assert error_code(response) == "ALLOCATION_EXCEEDS"
    response = shop.pay("purchase", "500", [{"document_id": doc["id"], "amount": "1000"}])
    assert error_code(response) == "ALLOCATION_OVER_TOTAL"


def test_ledger_and_aging(shop: Shop) -> None:
    old = created(shop.buy_poison("1", "1000", date=day(-50), due_date=day(-40)))["document"]
    created(shop.buy_poison("1", "1000", number="124"))
    created(shop.pay("purchase", "1000", [{"document_id": old["id"], "amount": "1000"}]))
    ledger = shop.c.get(
        f"/api/v1/current-accounts/{shop.supplier}", params={"direction": "purchase"}
    ).json()
    assert [Decimal(r["balance"]) for r in ledger["rows"]] == [
        Decimal("1210"),  # factura vieja
        Decimal("2420"),  # factura nueva (día -5)
        Decimal("1420"),  # pago (día -1)
    ]
    balances = shop.c.get("/api/v1/current-accounts", params={"direction": "purchase"}).json()
    row = next(b for b in balances if b["party"]["id"] == shop.supplier)
    assert Decimal(row["balance"]) == Decimal("1420")
    assert Decimal(row["days_31_60"]) == Decimal("210")  # vencida hace 40 días
    assert Decimal(row["overdue"]) == Decimal("210")


def test_lowering_total_trims_allocation(shop: Shop) -> None:
    doc = created(shop.buy_poison("10", "1000"))["document"]  # 12.100
    payment = created(
        shop.pay("purchase", "12100", [{"document_id": doc["id"], "amount": "12100"}])
    )
    body = {
        "direction": "purchase",
        "party_id": shop.supplier,
        "date": day(-5),
        "letter": "A",
        "pos_number": "3",
        "number": "123",
        "warehouse_id": shop.warehouse,
        "lines": [
            {
                "kind": "product",
                "product_id": shop.poison,
                "unit_id": shop.unit["L"],
                "quantity": "5",
                "unit_price": "1000",
            }
        ],
    }
    created(shop.c.put(f"/api/v1/commercial-documents/{doc['id']}", json=body))
    after = shop.c.get(f"/api/v1/payments/{payment['id']}").json()
    assert Decimal(after["allocated"]) == Decimal("6050")
    assert Decimal(after["unallocated"]) == Decimal("6050")


def test_cancel_document_frees_allocations(shop: Shop) -> None:
    doc = created(shop.buy_poison("1", "1000"))["document"]
    payment = created(shop.pay("purchase", "1210", [{"document_id": doc["id"], "amount": "1210"}]))
    created(shop.c.post(f"/api/v1/commercial-documents/{doc['id']}/cancel"))
    after = shop.c.get(f"/api/v1/payments/{payment['id']}").json()
    assert after["allocations"] == []
    assert Decimal(after["unallocated"]) == Decimal("1210")


def test_pending_filter_lists_only_unpaid(shop: Shop) -> None:
    paid = created(shop.buy_poison("1", "1000"))["document"]
    created(shop.buy_poison("1", "1000", number="124"))
    created(shop.pay("purchase", "1210", [{"document_id": paid["id"], "amount": "1210"}]))
    items = shop.c.get(
        "/api/v1/commercial-documents",
        params={"direction": "purchase", "party_id": shop.supplier, "only_pending": True},
    ).json()["items"]
    assert [i["invoice_label"] for i in items] == ["Factura A 00003-00000124"]


# --- Caja y bancos ---


def test_cash_balances_and_statement(shop: Shop) -> None:
    movement = {"date": day(-3), "cash_account_id": shop.cash, "amount": "30000"}
    created(
        shop.c.post(
            "/api/v1/cash/movements",
            json=movement | {"kind": "transfer", "target_account_id": shop.bank},
        )
    )
    created(
        shop.c.post(
            "/api/v1/cash/movements",
            json=movement | {"kind": "withdrawal", "amount": "10000", "description": "Retiro"},
        )
    )
    created(
        shop.c.post(
            "/api/v1/cash/movements",
            json=movement | {"kind": "income", "amount": "5000", "description": "Aporte"},
        )
    )
    assert shop.cash_balance(shop.cash) == Decimal("65000")
    assert shop.cash_balance(shop.bank) == Decimal("30000")
    statement = shop.c.get(
        f"/api/v1/cash/accounts/{shop.cash}/statement", params={"date_from": day(-3)}
    ).json()
    assert Decimal(statement["opening_balance"]) == Decimal("100000")
    assert Decimal(statement["closing_balance"]) == Decimal("65000")
    assert len(statement["rows"]) == 3


def test_transfer_needs_other_account(shop: Shop) -> None:
    body = {"date": day(-1), "kind": "transfer", "cash_account_id": shop.cash, "amount": "1"}
    assert error_code(shop.c.post("/api/v1/cash/movements", json=body)) == "TARGET"


def test_cancelled_movement_does_not_count(shop: Shop) -> None:
    body = {
        "date": day(-1),
        "kind": "withdrawal",
        "cash_account_id": shop.cash,
        "amount": "1000",
        "description": "Retiro",
    }
    movement = created(shop.c.post("/api/v1/cash/movements", json=body))
    created(shop.c.post(f"/api/v1/cash/movements/{movement['id']}/cancel"))
    assert shop.cash_balance(shop.cash) == Decimal("100000")


def test_movement_before_opening_is_rejected(shop: Shop) -> None:
    body = {
        "date": day(-90),
        "kind": "income",
        "cash_account_id": shop.cash,
        "amount": "1",
        "description": "x",
    }
    assert error_code(shop.c.post("/api/v1/cash/movements", json=body)) == "BEFORE_OPENING"


# --- Permisos ---


def test_staff_can_operate_and_read_only_cannot(client: TestClient, db: Session) -> None:
    login_as(client, db, STAFF)
    assert (
        client.get("/api/v1/commercial-documents", params={"direction": "sale"}).status_code == 200
    )
    assert client.get("/api/v1/cash/balances").status_code == 200
    login_as(client, db, READ_ONLY)
    assert (
        client.get("/api/v1/commercial-documents", params={"direction": "sale"}).status_code == 200
    )
    body = {"name": "Caja chica", "kind": "cash", "opening_date": TODAY.isoformat()}
    assert client.post("/api/v1/cash-accounts", json=body).status_code == 403


def test_sale_from_chosen_batch(shop: Shop, db: Session) -> None:
    cycle = shop.cycle()
    shop.harvest(cycle["id"], "10")
    second = shop.operation(
        [{"crop_cycle_id": cycle["id"]}],
        type_="Cosecha",
        date=day(-3),
        harvest={
            "unit_id": shop.unit["cajón"],
            "quantity": "8",
            "warehouse_id": shop.warehouse,
            "is_final": False,
        },
    )
    assert second.status_code == 201, second.json()
    params = {"product_id": shop.tomato, "warehouse_id": shop.warehouse}
    batches = shop.c.get("/api/v1/stock/batches", params=params).json()
    assert [Decimal(b["quantity"]) for b in batches] == [Decimal(10), Decimal(8)]
    newest = batches[1]["id"]

    doc = created(shop.sale("5", lines_batch=newest))["document"]
    moves = db.scalars(
        select(StockMove).where(StockMove.document_id == doc["stock_document_id"])
    ).all()
    assert [(m.quantity, str(m.batch_id)) for m in moves] == [(Decimal(-5), newest)]
    assert error_code(shop.sale("4", lines_batch=newest)) == "BATCH_STOCK"


# --- Nota de crédito asociada y devolución a la partida ---


def credit_note(shop: Shop, related: str | None, amount: str = "1000", **extra: Any) -> Any:
    line = {
        "kind": "expense",
        "expense_category_id": shop.category["Otros gastos"],
        "description": "Bonificación",
        "unit_price": amount,
        "vat_rate": "0",
    }
    body = {"kind": "credit_note", "number": "77", "related_document_id": related} | extra
    return shop.purchase([line], warehouse_id=None, **body)


def test_related_credit_note_lowers_pending(shop: Shop) -> None:
    invoice = created(shop.buy_poison("1", "1000"))["document"]  # 1.210
    created(credit_note(shop, invoice["id"], "210"))
    detail = shop.c.get(f"/api/v1/commercial-documents/{invoice['id']}").json()
    assert Decimal(detail["credited"]) == Decimal("210")
    assert Decimal(detail["pending"]) == Decimal("1000")
    assert error_code(credit_note(shop, invoice["id"], "1001", number="78")) == "CREDIT_EXCEEDS"
    cancel = shop.c.post(f"/api/v1/commercial-documents/{invoice['id']}/cancel")
    assert error_code(cancel) == "HAS_CREDIT_NOTES"


def test_credit_note_on_paid_invoice_leaves_advance(shop: Shop) -> None:
    invoice = created(shop.buy_poison("1", "1000"))["document"]
    payment = created(
        shop.pay("purchase", "1210", [{"document_id": invoice["id"], "amount": "1210"}])
    )
    created(credit_note(shop, invoice["id"], "210"))
    after = shop.c.get(f"/api/v1/payments/{payment['id']}").json()
    assert Decimal(after["unallocated"]) == Decimal("210")


def test_unrelated_credit_note_counts_as_advance(shop: Shop) -> None:
    created(credit_note(shop, None, "500"))
    balances = shop.c.get("/api/v1/current-accounts", params={"direction": "purchase"}).json()
    row = next(b for b in balances if b["party"]["id"] == shop.supplier)
    assert Decimal(row["advances"]) == Decimal("500")
    assert Decimal(row["balance"]) == Decimal("-500")


def test_sale_credit_note_returns_to_batch(shop: Shop, db: Session) -> None:
    cycle = shop.cycle()
    shop.harvest(cycle["id"], "10")
    params = {"product_id": shop.tomato, "warehouse_id": shop.warehouse}
    batch = shop.c.get("/api/v1/stock/batches", params=params).json()[0]["id"]
    sale = created(shop.sale("10"))["document"]
    assert shop.c.get("/api/v1/stock/batches", params=params).json() == []
    empty = shop.c.get("/api/v1/stock/batches", params=params | {"only_available": False})
    assert [b["id"] for b in empty.json()] == [batch]
    created(shop.sale("3", kind="credit_note", lines_batch=batch, related_document_id=sale["id"]))
    batches = shop.c.get("/api/v1/stock/batches", params=params).json()
    assert [(b["id"], Decimal(b["quantity"])) for b in batches] == [(batch, Decimal(3))]
