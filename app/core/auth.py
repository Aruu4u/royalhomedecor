from typing import Annotated

import httpx
from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from app.core.config import get_settings
from app.schemas.auth import AuthenticatedUser


bearer_scheme = HTTPBearer(
    auto_error=False,
)
settings = get_settings()


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthenticatedUser:
    """Validate a Supabase access token and return its user."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Bearer token is required.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    access_token = credentials.credentials

    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {access_token}",
    }

    auth_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
        ) as client:
            response = await client.get(
                auth_url,
                headers=headers,
            )

    except httpx.RequestError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is currently unavailable.",
        ) from exception

    if response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The access token is invalid or expired.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if response.is_error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service returned an unexpected response.",
        )

    try:
        return AuthenticatedUser.model_validate(
            response.json(),
        )

    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service returned invalid user data.",
        ) from exception


CurrentUserDependency = Annotated[
    AuthenticatedUser,
    Depends(get_current_user),
]


async def require_admin(
    current_user: CurrentUserDependency,
) -> AuthenticatedUser:
    """Require an authenticated user with the admin role."""

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )

    return current_user


AdminUserDependency = Annotated[
    AuthenticatedUser,
    Depends(require_admin),
]
