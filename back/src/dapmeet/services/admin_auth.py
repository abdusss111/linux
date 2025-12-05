import os
import datetime as dt
from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# Environment-driven admin auth configuration
ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


admin_oauth2_scheme = HTTPBearer()


def verify_admin_credentials(username: str, password: str) -> Dict[str, Any]:
    """Verify admin credentials against environment configuration.

    Returns a simple admin identity dict on success.
    """
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return {
            "sub": username,
            "username": username,
            "role": "admin",
        }
    raise HTTPException(status_code=401, detail="Invalid admin credentials")


def create_admin_jwt(admin_identity: Dict[str, Any], expires_minutes: int = 60 * 24) -> str:
    """Create a signed JWT for the admin using the admin secret.
    Includes role=admin claim and expiration.
    """
    now = dt.datetime.utcnow()
    exp = now + dt.timedelta(minutes=expires_minutes)
    payload = {
        **admin_identity,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, ADMIN_JWT_SECRET, algorithm="HS256")


def get_current_admin(
    token: HTTPAuthorizationCredentials = Depends(admin_oauth2_scheme),
):
    """FastAPI dependency to authorize admin-only routes.
    Verifies token with the admin secret and ensures role=admin.
    """
    try:
        payload = jwt.decode(token.credentials, ADMIN_JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    return payload


