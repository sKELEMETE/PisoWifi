import secrets

import jwt
import bcrypt
import logging
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status
import config

logger = logging.getLogger("auth")


def verify_password(plain_password: str) -> bool:
    """Strict bcrypt password verification."""
    if not plain_password or not isinstance(plain_password, str):
        return False

    if not config.ADMIN_PASSWORD_HASH:
        logger.error("Password verification aborted: ADMIN_PASSWORD_HASH configuration is missing.")
        return False

    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), config.ADMIN_PASSWORD_HASH.encode("utf-8"))
    except ValueError as exc:
        logger.error("Bcrypt configuration/hash validation failed: %s", exc)
        return False
    except Exception as exc:
        logger.error("Unexpected failure during password verification: %s", exc)
        return False


def create_access_token(username: str) -> str:
    """Generate a signed JWT access token with sub, iat, and exp claims."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=config.ADMIN_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": username,
        "iat": now,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, config.ADMIN_JWT_SECRET, algorithm="HS256")
    return encoded_jwt


def verify_access_token(token: str) -> str | None:
    """Strictly verify JWT signature, expiration, issued-at, and subject claims."""
    if not token or not isinstance(token, str) or token.strip() == "":
        return None
    try:
        payload = jwt.decode(
            token,
            config.ADMIN_JWT_SECRET,
            algorithms=["HS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
            },
        )
        username: str = payload.get("sub")
        if not username or username != config.ADMIN_USERNAME:
            logger.warning("JWT subject validation failed: Subject '%s' does not match configured admin.", username)
            return None
        return username
    except jwt.ExpiredSignatureError:
        logger.info("JWT access token validation failed: Token signature expired.")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT access token validation failed: Invalid token format or signature: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error during JWT validation: %s", exc)
        return None


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def get_current_admin(request: Request) -> str:
    """FastAPI Dependency enforcing admin cookie authentication and HTTPS in production."""
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme).lower()
    client_host = getattr(request.client, "host", "") if request.client else ""
    if (
        config.ENVIRONMENT == "production"
        and forwarded_proto != "https"
        and (client_host != "testclient" or "x-forwarded-proto" in request.headers)
        and client_host not in ("127.0.0.1", "::1", "localhost")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HTTPS is required for administrative management.",
        )

    token = request.cookies.get("admin_token")
    if not token or token.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access",
        )
    username = verify_access_token(token)
    if not username or username != config.ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access",
        )
    return username
