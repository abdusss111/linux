# src/dapmeet/cmd/main.py
import sys
import os
from pathlib import Path

# Настраиваем пути ДО импорта FastAPI и других модулей
def setup_paths():
    """
    Настраивает пути для корректной работы как через run.py, так и через uvicorn напрямую
    """
    # Получаем абсолютный путь к корню проекта
    # Структура: project_root/src/dapmeet/cmd/main.py
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent  # Поднимаемся на 4 уровня вверх
    src_path = project_root / "src"
    
    # Добавляем src в sys.path если его там нет
    src_path_str = str(src_path)
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)
    
    # Устанавливаем рабочую директорию в корень проекта (где находится .env)
    if os.getcwd() != str(project_root):
        os.chdir(str(project_root))

# Вызываем настройку путей ПЕРЕД всеми импортами
setup_paths()

# Теперь можно импортировать модули
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
import httpx
import logging

logger = logging.getLogger(__name__)

# Middleware для логирования всех запросов к endpoints маппинга
class MappingLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "/participants" in str(request.url.path):
            log_msg = (
                f"[MAPPING-REQUEST] {request.method} {request.url.path} - "
                f"client={request.client.host if request.client else 'unknown'}, "
                f"headers_authorization={'present' if 'authorization' in dict(request.headers) else 'missing'}"
            )
            logger.info(log_msg)
            print(log_msg)  # Дублируем в stdout
            
            # Пробуем прочитать body для логирования (если это POST)
            if request.method == "POST":
                try:
                    body_bytes = await request.body()
                    if body_bytes:
                        body_str = body_bytes.decode('utf-8', errors='replace')[:500]  # Первые 500 символов
                        log_msg_body = f"[MAPPING-REQUEST-BODY] {request.url.path}: {body_str}"
                        logger.info(log_msg_body)
                        print(log_msg_body)
                    
                    # Восстанавливаем body для последующего использования
                    async def receive():
                        return {"type": "http.request", "body": body_bytes}
                    request._receive = receive
                except Exception as e:
                    logger.warning(f"[MAPPING-REQUEST] Failed to read body: {e}")
        
        response = await call_next(request)
        
        # Логируем ответ
        if "/participants" in str(request.url.path):
            log_msg_response = (
                f"[MAPPING-RESPONSE] {request.method} {request.url.path} - "
                f"status_code={response.status_code}"
            )
            logger.info(log_msg_response)
            print(log_msg_response)
        
        return response

# Загружаем .env файл
load_dotenv()

# Импортируем роутер после настройки всех путей
from dapmeet.api import api_router as main_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create shared HTTP client
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
    )
    try:
        yield
    finally:
        # Shutdown: close HTTP client
        await app.state.http_client.aclose()


app = FastAPI(
    title="Dapmeet API",
    description="API for Dapmeet meeting transcription service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавляем middleware для логирования запросов маппинга ПЕРЕД CORS
app.add_middleware(MappingLoggingMiddleware)

app.include_router(main_router)

@app.get("/")
async def root():
    return {"message": "Dapmeet API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for Render monitoring"""
    return {"status": "healthy", "timestamp": "2025-01-27T00:00:00Z"}
