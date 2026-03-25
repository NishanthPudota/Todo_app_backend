"""
Alembic environment configuration.

This file is loaded by Alembic every time a migration command is run.
It wires together:
  - Your SQLAlchemy Base (so Alembic can detect model changes)
  - Your DATABASE_URL from app.config (reads .env automatically)
  - Both "offline" (SQL script) and "online" (live DB) migration modes
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make sure the project root is on the path so `app.*` imports work ──────────
# When Alembic runs from the project root (Todo_backend/) this is already true,
# but this guard makes it work from any working directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Import your models so Alembic can detect schema changes ────────────────────
# Importing Base alone is enough — as long as all model modules have been
# imported somewhere before this point so their Table objects are registered.
from app.models.database import Base  # noqa: F401 — registers User + Task
from app.config import settings       # reads DATABASE_URL from .env

# ── Alembic Config object (gives access to alembic.ini values) ─────────────────
config = context.config

# Interpret the config file for Python logging (if present)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Point Alembic at our metadata so --autogenerate works ──────────────────────
target_metadata = Base.metadata

# ── Inject the real DATABASE_URL from settings (overrides blank in alembic.ini) ─
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# ──────────────────────────────────────────────────────────────────────────────
# Offline mode  —  generates a .sql file without connecting to the database
# ──────────────────────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Produces a SQL script that can be reviewed and run manually.
    Useful when you don't have direct DB access (e.g. production).
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render the server_default so generated SQL is complete
        render_as_batch=False,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ──────────────────────────────────────────────────────────────────────────────
# Online mode  —  connects to the database and runs migrations directly
# ──────────────────────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an actual database connection and applies migrations immediately.
    This is the mode used by `alembic upgrade head`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # use NullPool in migrations — no connection pooling needed
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,      # detect column type changes
            compare_server_default=True,  # detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
