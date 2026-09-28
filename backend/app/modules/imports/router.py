"""Importación desde Excel: catálogo, plantilla, vista previa y confirmación (ADR-021)."""

from fastapi import APIRouter, Response, UploadFile

from app.core.db import DbSession
from app.core.errors import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.imports import IMPORTS, ImportDef, ImportResult, run_import, template
from app.core.schemas import Schema
from app.modules.identity.authorization import effective_permissions
from app.modules.identity.dependencies import CurrentUser
from app.modules.identity.models import User

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_BYTES = 5 * 1024 * 1024


class ImportColumnOut(Schema):
    key: str
    label: str
    required: bool
    help: str
    example: str


class ImportInfo(Schema):
    key: str
    title: str
    description: str
    columns: list[ImportColumnOut]


def _allowed(user: User, key: str) -> ImportDef:
    definition = IMPORTS.get(key)
    if definition is None:
        raise NotFoundError("No existe esa importación.")
    if definition.permission.code not in effective_permissions(user.role):
        raise ForbiddenError(f"No tenés permiso para importar: {definition.title}.")
    return definition


def _content(file: UploadFile) -> bytes:
    content = file.file.read()
    if len(content) > MAX_BYTES:
        raise BusinessRuleError("El archivo supera los 5 MB.", code="FILE_TOO_BIG")
    return content


# Orden de carga: cada importación usa lo cargado en las anteriores
LOAD_ORDER = ["products", "parties", "opening_stock", "opening_balances"]


def _load_position(definition: ImportDef) -> int:
    key = definition.key
    return LOAD_ORDER.index(key) if key in LOAD_ORDER else len(LOAD_ORDER)


@router.get("")
def list_imports(user: CurrentUser) -> list[ImportInfo]:
    permissions = effective_permissions(user.role)
    return [
        ImportInfo(
            key=d.key,
            title=d.title,
            description=d.description,
            columns=[ImportColumnOut(**c.__dict__) for c in d.columns],
        )
        for d in sorted(IMPORTS.values(), key=_load_position)
        if d.permission.code in permissions
    ]


@router.get("/{key}/template", response_class=Response, responses={200: {"content": {XLSX: {}}}})
def download_template(key: str, user: CurrentUser) -> Response:
    definition = _allowed(user, key)
    return Response(
        content=template(definition),
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="plantilla-{key}.xlsx"'},
    )


@router.post("/{key}/preview")
def preview_import(key: str, file: UploadFile, db: DbSession, user: CurrentUser) -> ImportResult:
    """Valida todo el archivo con las reglas reales y no guarda nada."""
    return run_import(db, _allowed(user, key), _content(file), commit=False)


@router.post("/{key}")
def confirm_import(key: str, file: UploadFile, db: DbSession, user: CurrentUser) -> ImportResult:
    """Importa si no hay errores (todo o nada)."""
    return run_import(db, _allowed(user, key), _content(file), commit=True)
