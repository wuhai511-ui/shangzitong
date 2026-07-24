import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Ensure app/ is on sys.path so `import models` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from models.base import Base  # noqa: E402

# Import all models so they register with Base.metadata
import models.user  # noqa: E402, F401
import models.card  # noqa: E402, F401
import models.datasource  # noqa: E402, F401
import models.sftp_config  # noqa: E402, F401
import models.email_config  # noqa: E402, F401
import models.bank  # noqa: E402, F401
import models.merchant_profile  # noqa: E402, F401
import models.manual_settlement  # noqa: E402, F401
import models.agency  # noqa: E402, F401
import models.agency_payment_channel  # noqa: E402, F401
import models.merchant  # noqa: E402, F401
import models.merchant_onboarding  # noqa: E402, F401
import models.onboarding_invite  # noqa: E402, F401
import models.onboarding_session  # noqa: E402, F401
import models.transaction  # noqa: E402, F401
import models.auto_swipe_policy  # noqa: E402, F401
import models.auto_swipe_execution_log  # noqa: E402, F401

config = context.config
target_metadata = Base.metadata

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
