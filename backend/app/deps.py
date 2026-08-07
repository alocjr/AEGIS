from bson import ObjectId
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pymongo.database import Database

from app.config import settings
from app.database import get_db
from app.security import _jwt_key_bytes
from app.tools import user_has_tool
from app.utils.auth_cookie import AUTH_COOKIE_NAME


bearer_scheme = HTTPBearer(auto_error=False)


def is_email_verified(user: dict) -> bool:
    """Usuários legados sem o campo são tratados como verificados."""
    return user.get("email_verified") is not False


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Database = Depends(get_db),
):
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token and credentials is not None:
        token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nao autenticado")

    try:
        payload = jwt.decode(
            token,
            _jwt_key_bytes(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido") from exc

    user_id = payload.get("sub")
    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")

    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao encontrado")

    return user


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Database = Depends(get_db),
):
    """Usuário logado quando houver sessão válida, `None` caso contrário — sem nunca bloquear.

    Para rotas públicas que só querem enriquecer o registro com a identidade de quem já está
    logado (ex.: contagem de acesso), um token ausente ou vencido não é erro.
    """
    try:
        return get_current_user(request, credentials, db)
    except HTTPException:
        return None


def get_verified_user(user=Depends(get_current_user)):
    if not is_email_verified(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirme seu email antes de acessar este recurso.",
        )
    return user


def get_current_admin(user=Depends(get_verified_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return {**user, "is_admin": True}


def get_current_org_admin(user=Depends(get_verified_user)):
    """Admin da plataforma OU admin da própria organização (gestão de membros, sem trilha)."""
    if not (user.get("is_admin") or user.get("is_org_admin")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores da organização",
        )
    return user


def require_tool(tool_id: str):
    """Dependência de router: bloqueia a ferramenta que o admin não liberou para o usuário.

    Aplicada no `APIRouter` inteiro (não endpoint por endpoint) para uma rota nova nascer
    protegida. O `tool_id` fica exposto na função para o teste conferir que todo router de
    ferramenta declara a sua trava.
    """

    def dependency(user=Depends(get_verified_user)):
        if not user_has_tool(user, tool_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "TOOL_NOT_ENABLED",
                    "message": "Esta ferramenta não está habilitada para o seu acesso.",
                    "tool": tool_id,
                },
            )
        return user

    dependency.tool_id = tool_id
    return dependency


def get_current_organization_id(user=Depends(get_verified_user)) -> ObjectId:
    """Organizacao do usuario logado — chave de escopo para dados compartilhados pelo time."""
    org_id = user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuario sem organizacao atribuida. Contate o suporte.",
        )
    return org_id
