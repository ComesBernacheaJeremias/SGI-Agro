import sentry_sdk
from fastapi import FastAPI

from app import (  # noqa: F401  (registran permisos, reportes e importaciones)
    imports,
    permissions,
    reports,
)
from app.core import health
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, request_logging_middleware
from app.core.ratelimit import rate_limit_middleware
from app.modules.assets import router as assets
from app.modules.audit import router as audit
from app.modules.commercial import router as commercial
from app.modules.costs import router as costs
from app.modules.identity import auth_router, role_router, user_router
from app.modules.imports import router as imports_router
from app.modules.inventory import router as inventory
from app.modules.manufacturing import router as manufacturing
from app.modules.masterdata import router as masterdata
from app.modules.production import router as production
from app.modules.reports import dashboard
from app.modules.reports import router as reports_router


def create_app() -> FastAPI:
    settings = get_settings()
    settings.check_production()
    configure_logging(json=settings.is_production)
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            release=settings.app_version,
            send_default_pii=False,  # sin datos personales
            traces_sample_rate=0,
        )

    # En producción no se publica la documentación de la API
    docs = not settings.is_production
    app = FastAPI(
        title="SGI Agro API",
        version=settings.app_version,
        docs_url="/api/docs" if docs else None,
        redoc_url="/api/redoc" if docs else None,
        openapi_url="/api/openapi.json" if docs else None,
    )
    app.middleware("http")(request_logging_middleware)
    if settings.is_production:
        app.middleware("http")(rate_limit_middleware(settings.api_rate_limit_per_minute))
    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(auth_router.router)
    app.include_router(user_router.router)
    app.include_router(role_router.router)
    app.include_router(role_router.permissions_router)
    app.include_router(audit.router)
    for router in [
        *masterdata.routers,
        *inventory.routers,
        *assets.routers,
        *production.routers,
        *manufacturing.routers,
        *commercial.routers,
        costs.router,
        reports_router.router,
        dashboard.router,
        imports_router.router,
    ]:
        app.include_router(router)
    return app


app = create_app()
