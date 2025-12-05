from fastapi import APIRouter

from . import meetings, chat, auth, admin, admin_prompts, user_prompts, whisper, webhook, subscription

api_router = APIRouter()
api_router.include_router(meetings.router, prefix="/api/meetings", tags=["Meetings"])
api_router.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(subscription.router, prefix="/api/subscriptions", tags=["Subscriptions"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(admin_prompts.router, prefix="/admin/prompts", tags=["Admin Prompts"])
api_router.include_router(user_prompts.router, prefix="/api/prompts", tags=["User Prompts"])
api_router.include_router(whisper.router, prefix="/api/whisper", tags=["Whisper"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])