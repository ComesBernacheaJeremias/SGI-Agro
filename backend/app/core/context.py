"""Datos del request en curso (request id y usuario), accesibles desde cualquier capa.

FastAPI ejecuta las dependencias y endpoints sincrónicos en hilos distintos y cada hilo recibe
una *copia* del contexto: lo que se asigna a una ContextVar en un hilo no llega al otro. Por eso
el middleware crea un objeto `RequestContext` por request y todos los hilos modifican ese mismo
objeto (la copia del contexto apunta al mismo objeto).
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID


@dataclass
class RequestContext:
    request_id: str | None = None
    user_id: UUID | None = None


_current: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def start_request(request_id: str) -> Token[RequestContext | None]:
    return _current.set(RequestContext(request_id=request_id))


def end_request(token: Token[RequestContext | None]) -> None:
    _current.reset(token)


def current() -> RequestContext:
    """Contexto del request actual (fuera de un request —CLI, tests— crea uno vacío)."""
    context = _current.get()
    if context is None:
        context = RequestContext()
        _current.set(context)
    return context
