from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from dapmeet.core.deps import get_async_db, get_http_client
from dapmeet.schemas.auth import (
    CodePayload, 
    PhoneAuthRequest, 
    PhoneVerificationRequest,
    PhoneAuthResponse,
    PhoneVerificationResponse
)
from dapmeet.services.google_auth_service import (
    authenticate_with_google_token,
    exchange_code_for_token,
    get_google_user_info,
    find_or_create_user,
    generate_jwt
)
from dapmeet.services.subscription import SubscriptionService
# from dapmeet.services.phone_auth_service import (
#     create_phone_verification,
#     verify_phone_code,
#     find_or_create_phone_user,
#     generate_phone_jwt,
#     send_verification_code,
#     cleanup_expired_verifications
# )

router = APIRouter()

@router.post("/google")
async def google_auth(
    payload: CodePayload, 
    db: AsyncSession = Depends(get_async_db),
    http_client: httpx.AsyncClient = Depends(get_http_client)
):
    access_token = await exchange_code_for_token(payload.code, http_client)
    user_info = await get_google_user_info(access_token, http_client)
    user = await find_or_create_user(user_info, db)
    jwt_token = generate_jwt(user_info)
    
    # Get subscription status
    subscription_service = SubscriptionService(db)
    subscription_info = await subscription_service.verify_subscription(user.id)

    return {
        "access_token": jwt_token, 
        "user": user_info,
        "subscription": {
            "plan": subscription_info.plan,
            "status": subscription_info.status,
            "features": subscription_info.features.dict()
        }
    }

@router.post("/validate")
async def validate_chrome_extension_auth(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    http_client: httpx.AsyncClient = Depends(get_http_client)
):
    # Получаем Google access token из заголовка
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid auth header")
    
    google_token = auth_header.split(" ")[1]
    
    # Аутентифицируем пользователя
    user, jwt_token = await authenticate_with_google_token(google_token, db, http_client)
    
    # Get subscription status
    subscription_service = SubscriptionService(db)
    subscription_info = await subscription_service.verify_subscription(user.id)
    
    return {
        "token": jwt_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        },
        "subscription": {
            "plan": subscription_info.plan,
            "status": subscription_info.status,
            "features": subscription_info.features.dict()
        }
    }

