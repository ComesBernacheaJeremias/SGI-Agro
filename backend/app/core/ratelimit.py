"""Tope de pedidos por IP (ventana deslizante de 1 minuto, en memoria de cada proceso).

Frena a un script que martilla la API; el uso normal (una pantalla dispara 10-20 pedidos)
queda muy lejos del tope. Con varios procesos cada uno cuenta aparte: el tope real es algo
mayor, suficiente para este fin. El login además tiene su propio tope por IP en la base.
"""

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

WINDOW_SECONDS = 60.0


class RateLimiter:
    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self.hits[key]
        while hits and hits[0] <= now - WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= self.per_minute:
            return False
        hits.append(now)
        if len(self.hits) > 10_000:  # no crecer sin límite con IPs de una sola vez
            for ip in [k for k, v in self.hits.items() if not v]:
                del self.hits[ip]
        return True


def rate_limit_middleware(
    per_minute: int,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    limiter = RateLimiter(per_minute)

    async def middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        ip = request.client.host if request.client else "?"
        if request.url.path.startswith("/api/") and not limiter.allow(ip):
            body = {
                "error": {
                    "code": "TOO_MANY_REQUESTS",
                    "message": "Demasiados pedidos seguidos. Esperá un momento y volvé a intentar.",
                    "details": {},
                }
            }
            return JSONResponse(body, status_code=429, headers={"Retry-After": "60"})
        return await call_next(request)

    return middleware
