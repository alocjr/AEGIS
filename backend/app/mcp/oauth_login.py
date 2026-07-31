"""Página de login OAuth Valorian (Claude Connectors → browser)."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.mcp.oauth_provider import authenticate_user_for_oauth, complete_login_with_code
from app.mcp.oauth_store import get_pending

router = APIRouter(tags=["mcp-oauth"])

_LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Conectar Claude · Valorian</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a222c;
      --text: #f2f4f7;
      --muted: #9aa3af;
      --accent: #c4a35a;
      --err: #e85d5d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: radial-gradient(1200px 600px at 20% 0%, #243041, var(--bg));
      color: var(--text);
    }}
    form {{
      width: min(400px, 92vw); background: var(--card); padding: 28px 24px;
      border-radius: 12px; border: 1px solid rgba(255,255,255,0.06);
    }}
    h1 {{ margin: 0 0 6px; font-size: 1.35rem; font-weight: 600; }}
    p {{ margin: 0 0 20px; color: var(--muted); font-size: 0.92rem; line-height: 1.4; }}
    label {{ display: block; font-size: 0.8rem; color: var(--muted); margin: 12px 0 6px; }}
    input {{
      width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid #334155;
      background: #0f1720; color: var(--text); font-size: 1rem;
    }}
    button {{
      margin-top: 20px; width: 100%; padding: 12px; border: 0; border-radius: 8px;
      background: var(--accent); color: #1a1408; font-weight: 600; font-size: 1rem;
      cursor: pointer;
    }}
    button:hover {{ filter: brightness(1.05); }}
    .err {{
      background: rgba(232,93,93,0.12); color: #ffb4b4; padding: 10px 12px;
      border-radius: 8px; font-size: 0.88rem; margin-bottom: 12px;
    }}
  </style>
</head>
<body>
  <form method="post" action="/mcp-oauth/login">
    <h1>Valorian</h1>
    <p>Entre com sua conta para autorizar o Claude a usar a plataforma AEGIS.</p>
    {error}
    <input type="hidden" name="sid" value="{sid}" />
    <label for="email">Email</label>
    <input id="email" name="email" type="email" autocomplete="username" required />
    <label for="password">Senha</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required />
    <button type="submit">Autorizar Claude</button>
  </form>
</body>
</html>
"""


def _page(sid: str, error: str | None = None) -> HTMLResponse:
    err = f'<div class="err">{error}</div>' if error else ""
    return HTMLResponse(_LOGIN_HTML.format(sid=sid, error=err))


@router.get("/mcp-oauth/login", response_class=HTMLResponse)
def oauth_login_form(sid: str = ""):
    if not sid or not get_pending(sid):
        return HTMLResponse(
            "<h1>Sessão inválida</h1><p>Volte ao Claude e clique em Connect novamente.</p>",
            status_code=400,
        )
    return _page(sid)


@router.post("/mcp-oauth/login")
def oauth_login_submit(
    request: Request,
    sid: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    if not get_pending(sid):
        return _page(sid, "Sessão expirada. Recomece a conexão no Claude.")
    try:
        user = authenticate_user_for_oauth(email, password)
        redirect_url = complete_login_with_code(sid=sid, user_id=str(user["_id"]))
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Falha no login."
        return _page(sid, detail)
    except ValueError as exc:
        return _page(sid, str(exc))
    return RedirectResponse(url=redirect_url, status_code=302)
