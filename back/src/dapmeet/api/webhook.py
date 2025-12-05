"""
Webhook API endpoints for external service integration
"""

from fastapi import APIRouter, HTTPException, Request, Header, Depends
from datetime import datetime, timezone
import logging
import os
from typing import Optional

from dapmeet.schemas.webhook import WebhookEmailRequest, WebhookEmailResponse
from dapmeet.services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_webhook_key(x_webhook_key: Optional[str] = Header(None, alias="X-Webhook-Key")):
    """
    Verify webhook key from request headers
    
    Args:
        x_webhook_key: Webhook key from X-Webhook-Key header
        
    Raises:
        HTTPException: If webhook key is missing or invalid
    """
    expected_key = os.getenv("WEBHOOK_KEY")
    
    if not expected_key:
        logger.error("WEBHOOK_KEY environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="Webhook authentication not configured"
        )
    
    if not x_webhook_key:
        logger.warning("Webhook request missing X-Webhook-Key header")
        raise HTTPException(
            status_code=401,
            detail="Missing webhook key. Include X-Webhook-Key header."
        )
    
    if x_webhook_key != expected_key:
        logger.warning(f"Invalid webhook key provided: {x_webhook_key[:8]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook key"
        )
    
    return True


@router.post("/email", response_model=WebhookEmailResponse)
async def webhook_send_email(
    request: WebhookEmailRequest,
    raw_request: Request,
    _: bool = Depends(verify_webhook_key)
):
    """
    Webhook endpoint that receives requests from external services
    and sends welcome emails using the existing email service.
    
    Requires authentication via X-Webhook-Key header.
    
    Args:
        request: WebhookEmailRequest containing email and optional user_name
        raw_request: FastAPI Request object for logging purposes
        _: Webhook key verification dependency
    
    Returns:
        WebhookEmailResponse with success status and details
        
    Headers:
        X-Webhook-Key: Required authentication key (set via WEBHOOK_KEY env var)
    """
    try:
        # Log the incoming webhook request
        client_ip = raw_request.client.host if raw_request.client else "unknown"
        logger.info(f"Webhook email request received from {client_ip} for email: {request.email}")
        
        # Send welcome email using the existing email service
        # Use email address as user_name instead of the provided user_name
        success = await email_service.send_welcome_email(
            user_email=request.email,
            user_name=request.email
        )
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if success:
            logger.info(f"Welcome email sent successfully to {request.email}")
            return WebhookEmailResponse(
                success=True,
                message="Welcome email sent successfully",
                email_sent_to=request.email,
                timestamp=timestamp
            )
        else:
            logger.error(f"Failed to send welcome email to {request.email}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to send welcome email"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Webhook email processing failed for {request.email}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/health")
async def webhook_health_check():
    """
    Health check endpoint for webhook service
    """
    return {
        "status": "healthy",
        "service": "webhook",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
