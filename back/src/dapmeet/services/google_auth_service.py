import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from dapmeet.models.user import User
from dapmeet.services.email_service import email_service

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_ID_EXTENSION = os.getenv("GOOGLE_CLIENT_ID_EXTENSION")
GOOGLE_CLIENT_ID_EXTENSION_PROD = os.getenv("GOOGLE_CLIENT_ID_EXTENSION_PROD")

GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
GOOGLE_REDIRECT_URI_APP = os.getenv("GOOGLE_REDIRECT_URI_APP")
JWT_SECRET = os.getenv("NEXTAUTH_SECRET")


async def exchange_code_for_token(code: str, http_client: httpx.AsyncClient) -> str:
    """
    Обменивает authorization code на access token.
    Пытается использовать GOOGLE_REDIRECT_URI, а в случае неудачи - GOOGLE_REDIRECT_URI_APP.
    """
    
    redirect_uris = [
        GOOGLE_REDIRECT_URI,
        GOOGLE_REDIRECT_URI_APP
    ]
    
    # Variable to hold the error information if the last attempt fails
    last_error_detail = None

    for redirect_uri in redirect_uris:
        # Attempt the request
        token_resp = await http_client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Check for success
        if token_resp.status_code == 200:
            token_data = token_resp.json()
            # Success! Immediately return the token.
            return token_data["access_token"]
        
        # If it failed, record the error and continue to the next URI
        last_error_detail = f"Token exchange failed with URI '{redirect_uri}': {token_resp.text}"
    
    # If the loop finishes without a successful return, raise the last encountered error.
    if last_error_detail:
        raise HTTPException(
            status_code=400, 
            detail=f"All token exchange attempts failed. Last error: {last_error_detail}"
        )
    
    # Fallback (shouldn't happen if the list isn't empty)
    raise HTTPException(status_code=500, detail="Token exchange failed due to unexpected error.")


async def validate_google_access_token(access_token: str, http_client: httpx.AsyncClient) -> dict:
    """
    Валидирует Google access token и возвращает информацию о токене
    Проверяет audience для защиты от token substitution атак
    """
    token_info_resp = await http_client.get(
        f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
    )
    
    if token_info_resp.status_code != 200:
        raise HTTPException(
            status_code=401, 
            detail=f"Token validation failed: {token_info_resp.text}"
        )
    
    token_info = token_info_resp.json()
    
        # Критически важно: проверяем что токен выдан для нашего приложения
    is_extension = access_token.startswith("ya29.")  # признак «расширенного» токена

    # выбираем, с каким CLIENT_ID сравнивать
    if is_extension:
        # Для расширения проверяем оба возможных CLIENT_ID
        expected_audiences = [GOOGLE_CLIENT_ID_EXTENSION, GOOGLE_CLIENT_ID_EXTENSION_PROD]
        if token_info.get("audience") not in expected_audiences:
            raise HTTPException(
                status_code=401,
                detail="Token audience mismatch - token not issued for this extension application"
            )
    else:
        # Для обычного OAuth flow проверяем основной CLIENT_ID
        if token_info.get("audience") != GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=401,
                detail="Token audience mismatch - token not issued for this application"
            )
    # дальше – проверка срока жизни и т.п.


    # Проверяем что токен не истек
    if token_info.get("expires_in", 0) <= 0:
        raise HTTPException(
            status_code=401, 
            detail="Token has expired"
        )
    
    return token_info


async def get_google_user_info(access_token: str, http_client: httpx.AsyncClient) -> dict:
    """
    Получает информацию о пользователе из Google API
    Сначала валидирует токен для безопасности
    """    
    # Теперь безопасно получаем user info
    user_resp = await http_client.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if user_resp.status_code != 200:
        raise HTTPException(
            status_code=400, 
            detail=f"User info fetch failed: {user_resp.text}"
        )

    return user_resp.json()


async def validate_and_get_user_info(access_token: str, http_client: httpx.AsyncClient) -> dict:
    """
    Комбинированная функция: валидация токена + получение user info
    Для Chrome Identity API использования
    """
    # Валидируем токен
    token_info = await validate_google_access_token(access_token, http_client)
    
    # Получаем user info
    user_info = await get_google_user_info(access_token, http_client)
    
    # Возвращаем объединенную информацию
    return {
        **user_info,
        "token_info": {
            "audience": token_info.get("audience"),
            "scope": token_info.get("scope"),
            "expires_in": token_info.get("expires_in")
        }
    }


async def find_or_create_user(user_info: dict, db: AsyncSession) -> User:
    """
    Находит существующего пользователя или создает нового (async)
    Отправляет welcome email новым пользователям
    """
    result = await db.execute(select(User).where(User.id == user_info["id"]))
    user = result.scalar_one_or_none()
    is_new_user = False
    
    if not user:
        user = User(
            id=user_info["id"],
            email=user_info["email"],
            name=user_info.get("name", "")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    
    # Send welcome email to new users
    if is_new_user:
        try:
            await email_service.send_welcome_email(
                user_email=user.email,
                user_name=user.name
            )
        except Exception as e:
            # Log error but don't fail the registration process
            print(f"Failed to send welcome email to {user.email}: {str(e)}")
    
    return user


def generate_jwt(user_info: dict) -> str:
    """
    Генерирует кастомный JWT для использования в API
    """
    payload = {
        "sub": user_info["id"],
        "email": user_info["email"],
        "name": user_info.get("name", ""),
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def authenticate_with_google_token(access_token: str, db: AsyncSession, http_client: httpx.AsyncClient) -> tuple[User, str]:
    """
    Полный flow аутентификации для Chrome Identity:
    1. Валидирует Google токен
    2. Получает user info  
    3. Создает/находит пользователя в БД
    4. Генерирует кастомный JWT
    
    Returns: (User object, JWT token)
    """
    try:
        # Получаем и валидируем user info
        user_info = await validate_and_get_user_info(access_token, http_client)
        
        # Создаем/находим пользователя
        user = await find_or_create_user(user_info, db)
        
        # Генерируем наш JWT
        jwt_token = generate_jwt(user_info)
        
        return user, jwt_token
        
    except HTTPException:
        # Пробрасываем HTTP ошибки как есть
        raise
    except Exception as e:
        # Ловим любые другие ошибки
        raise HTTPException(
            status_code=500, 
            detail=f"Authentication failed: {str(e)}"
        )