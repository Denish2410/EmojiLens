from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context

from emojilens_api.db import Base, make_engine
from emojilens_api.db import models as _models  # noqa: F401  (register tables)

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

env_url = os.environ.get("EMOJILENS_DATABASE_URL")
url = config.get_main_option("sqlalchemy.url")
if env_url and url == "sqlite:///./var/emojilens.db":
    url = env_url
assert url is not None

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
