import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status
import config

def verify_password(plain_password: str) -> bool:
    if config.PLAINTEXT_MODE:
        return plain_password == config.ADMIN_PASSWORD
    
    if not config.ADMIN_PASSWORD_HASH:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), config.ADMIN_PASSWORD_HASH.encode("utf-8"))
    except Exception:
        return False

def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=config.ADMIN_TOKEN_EXPIRE_HOURS)
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, config.ADMIN_JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def verify_access_token(token: str) -> str | None:
    if not token:
        return None
    try:
        # Strictly verify signature, expiration, and algorithm to protect against algorithm confusion attacks
        payload = jwt.decode(token, config.ADMIN_JWT_SECRET, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

def get_current_admin(request: Request) -> str:
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
