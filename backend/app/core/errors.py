"""Errores de negocio y formato único de respuesta de error:

{ "error": { "code": "INSUFFICIENT_STOCK", "message": "...", "details": {...} } }
"""

from typing import Any, cast

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger()


class AppError(Exception):
    """Error esperado de la aplicación. `message` se muestra al usuario (en español)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"

    def __init__(
        self, message: str, *, code: str | None = None, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.details = details or {}


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class BusinessRuleError(AppError):
    """Una regla de negocio impide la operación (stock insuficiente, ciclo finalizado…)."""

    status_code = status.HTTP_409_CONFLICT
    code = "BUSINESS_RULE"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class TooManyRequestsError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "TOO_MANY_REQUESTS"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


def _error_response(
    status_code: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details or {}}}
    return JSONResponse(content=body, status_code=status_code)


# Starlette tipa los handlers con `Exception`; `cast` indica el tipo real que recibe cada uno.
async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    return _error_response(error.status_code, error.code, error.message, error.details)


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    errors = cast(RequestValidationError, exc).errors()
    fields = [
        {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]} for err in errors
    ]
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "VALIDATION_ERROR",
        "Hay datos inválidos en el formulario.",
        {"fields": fields},
    )


async def _http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    error = cast(StarletteHTTPException, exc)
    messages = {404: "Recurso no encontrado.", 405: "Método no permitido."}
    message = messages.get(error.status_code, str(error.detail))
    return _error_response(error.status_code, f"HTTP_{error.status_code}", message)


async def _unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unexpected_error", exc_info=exc)
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR",
        "Ocurrió un error inesperado. Intentá de nuevo.",
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)
