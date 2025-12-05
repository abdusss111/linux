import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context
from dotenv import load_dotenv

# Load environment variables from .env file
# Try to find .env file in the project root (parent of alembic directory)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dapmeet.db.db import Base
from dapmeet.models import user
from dapmeet.models import meeting
from dapmeet.models import segment
from dapmeet.models import chat_message
from dapmeet.models import subscription

target_metadata = Base.metadata

def get_url():
    url = config.get_main_option("sqlalchemy.url")
    if url is None:
        # Try DATABASE_URL first, then DATABASE_URL_ASYNC
        url = os.getenv("DATABASE_URL")
        if url is None:
            url_async = os.getenv("DATABASE_URL_ASYNC")
            if url_async:
                # Convert async URL to sync URL (remove asyncpg driver)
                url = url_async.replace("+asyncpg", "").replace("postgresql+asyncpg://", "postgresql://")
    return url

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=False,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
