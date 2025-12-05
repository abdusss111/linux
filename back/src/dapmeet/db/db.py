# Этот файл является центральной точкой для конфигурации базы данных.
# Он отвечает за:
# 1. Загрузку переменных окружения из файла .env (с помощью python-dotenv).
# 2. Создание SQLAlchemy `engine`, который является точкой входа к базе данных.
# 3. Создание `SessionLocal` для управления сессиями.
# 4. Определение `Base` для декларативных моделей SQLAlchemy.
#
# Любая часть приложения, которой нужен доступ к БД, должна импортировать
# объекты из этого файла.

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

# Загружаем переменные из .env файла
load_dotenv()

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_ASYNC = os.getenv("DATABASE_URL_ASYNC")

# Если DATABASE_URL не установлен, но есть DATABASE_URL_ASYNC, создаем синхронную версию
if DATABASE_URL is None and DATABASE_URL_ASYNC:
    # Convert async URL to sync URL (remove asyncpg driver)
    DATABASE_URL = DATABASE_URL_ASYNC.replace("+asyncpg", "").replace("postgresql+asyncpg://", "postgresql://")

# Проверяем, что переменная установлена
if DATABASE_URL is None:
    raise ValueError("DATABASE_URL or DATABASE_URL_ASYNC environment variable not set. Please create a .env file or set it manually.")

# Для async-режима требуется отдельный DSN с asyncpg-драйвером
if DATABASE_URL_ASYNC is None:
    # Разрешаем отсутствовать на раннем этапе миграции — но укажем подсказку
    # Реальное использование async-сессии упадет без этой переменной
    DATABASE_URL_ASYNC = None

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Async engine/session (используется постепенно)
async_engine = None
AsyncSessionLocal = None

if DATABASE_URL_ASYNC:
    # Add SSL for production (Render requires it)
    # IMPORTANT: Pool settings optimized for high-concurrency multi-instance deployment
    # 
    # Default settings are for 2-3 instances with 100 max_connections database:
    #   - 3 instances × (8 base + 22 overflow) = 90 max connections (safe margin under 100)
    # 
    # To customize, set environment variables:
    #   - DB_POOL_SIZE: base pool size per instance (default 8)
    #   - DB_POOL_MAX_OVERFLOW: max overflow per instance (default 22)
    
    pool_size = int(os.getenv("DB_POOL_SIZE", "8"))
    max_overflow = int(os.getenv("DB_POOL_MAX_OVERFLOW", "22"))
    
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": pool_size,  # Configurable base pool per instance
        "max_overflow": max_overflow,  # Configurable overflow per instance
        "pool_timeout": 45,  # Increased timeout for high-load scenarios
        "pool_recycle": 1800,  # Recycle connections every 30min (faster than before)
        "pool_reset_on_return": "rollback",  # Rollback to ensure clean state
        "echo_pool": False,  # Set to True for debugging connection pool issues
    }
    
    # Add SSL for production databases (Render requires it)
    if "sslmode=require" in DATABASE_URL_ASYNC:
        engine_kwargs["connect_args"] = {"sslmode": "require"}
    elif "render.com" in DATABASE_URL_ASYNC or ".internal" in DATABASE_URL_ASYNC:
        # Render databases require SSL even for internal connections
        engine_kwargs["connect_args"] = {"sslmode": "require"}
    
    async_engine = create_async_engine(DATABASE_URL_ASYNC, **engine_kwargs)
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
