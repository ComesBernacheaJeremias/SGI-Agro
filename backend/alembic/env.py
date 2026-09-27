"""Entorno de Alembic: usa la configuración de la app y todos los modelos registrados."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Los tests pasan su propia URL (base de tests) vía config.attributes["url"]
url = config.attributes.get("url") or get_settings().database_url()


def run_migrations_offline() -> None:
    context.configure(
        url=url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
