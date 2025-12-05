#!/usr/bin/env python3
"""Script to run database migrations"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Get DATABASE_URL or convert DATABASE_URL_ASYNC to sync format
database_url = os.getenv('DATABASE_URL')
database_url_async = os.getenv('DATABASE_URL_ASYNC')

if not database_url and database_url_async:
    # Convert async URL to sync URL (replace asyncpg with psycopg2)
    database_url = database_url_async.replace('+asyncpg', '').replace('postgresql+asyncpg://', 'postgresql://')
    # Set it as DATABASE_URL for Alembic
    os.environ['DATABASE_URL'] = database_url
    print(f"Using DATABASE_URL_ASYNC (converted to sync format)")
elif database_url:
    print(f"Using DATABASE_URL")
else:
    print("ERROR: Neither DATABASE_URL nor DATABASE_URL_ASYNC found in .env file")
    sys.exit(1)

# Run migrations
from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
print("Running migrations...")
command.upgrade(alembic_cfg, "head")
print("Migrations completed successfully!")

