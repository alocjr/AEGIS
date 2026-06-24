from fastapi import Response

from app.config import settings


AUTH_COOKIE_NAME = "access_token"


def _cookie_secure() -> bool:
    return settings.environment.lower() == "production"


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value="",
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        max_age=0,
        path="/",
    )
