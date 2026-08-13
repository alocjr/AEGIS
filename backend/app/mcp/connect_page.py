"""Página pública: como conectar o Claude ao AEGIS (URL do MCP)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.mcp.oauth_provider import mcp_public_base

router = APIRouter(tags=["mcp-oauth"])


@router.get("/conectar-claude", response_class=HTMLResponse)
def conectar_claude_page():
    base = mcp_public_base()
    mcp_url = f"{base}/mcp"
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Conectar Claude · Valorian AEGIS</title>
  <style>
    body {{ font-family: Georgia, "Times New Roman", serif; max-width: 40rem; margin: 3rem auto; padding: 0 1.25rem;
      background: #f7f3ea; color: #1c1917; line-height: 1.55; }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.35rem; }}
    .url {{ font-family: ui-monospace, monospace; background: #fff; border: 1px solid #d6d3d1;
      padding: 0.75rem 1rem; border-radius: 6px; word-break: break-all; margin: 1rem 0; }}
    ol {{ padding-left: 1.25rem; }}
    li {{ margin: 0.5rem 0; }}
    .muted {{ color: #57534e; font-size: 0.95rem; }}
    button {{ font: inherit; padding: 0.4rem 0.75rem; cursor: pointer; }}
    .callout {{ background: #fff; border: 1px solid #d6d3d1; border-left: 4px solid #b45309;
      padding: 0.85rem 1rem; border-radius: 6px; margin: 1.5rem 0; }}
    .callout h2 {{ font-size: 1.15rem; margin: 0 0 0.5rem; }}
  </style>
</head>
<body>
  <h1>Conectar o Claude à Valorian</h1>
  <p class="muted">Use esta URL no Claude (Connectors). O login é a mesma conta da plataforma.</p>
  <div class="url" id="mcp-url">{mcp_url}</div>
  <button type="button" onclick="navigator.clipboard.writeText(document.getElementById('mcp-url').textContent)">Copiar URL</button>
  <h2>Claude Desktop / claude.ai</h2>
  <ol>
    <li>Abra <strong>Settings → Connectors → Add custom connector</strong>.</li>
    <li>Cole a URL acima e confirme. Nome só com letras ASCII, sem espaços.</li>
    <li>Clique em <strong>Connect</strong> — o navegador abre o login Valorian.</li>
    <li>Entre com email e senha.</li>
    <li>No connector, <strong>Tool access</strong>: marque as tools novas como <strong>Allow always</strong>.</li>
  </ol>
  <h2>Claude Code</h2>
  <ol>
    <li><code>claude mcp add --transport http aegis {mcp_url}</code></li>
    <li>Na sessão, <code>/mcp</code> → autentique no browser.</li>
  </ol>
  <div class="callout">
    <h2>As tools novas não aparecem?</h2>
    <p>O Claude cacheia a lista de tools. O servidor já as anuncia; o chat antigo continua com o catálogo velho.</p>
    <ol>
      <li>Confirme o deploy (a URL acima precisa estar no ar com o código novo).</li>
      <li>No connector: habilite as tools novas (<strong>Allow always</strong>).</li>
      <li><strong>Remova o connector e adicione de novo</strong> (mesma URL). Só desconectar não basta.</li>
      <li>Abra um <strong>chat novo</strong> — conversas antigas não atualizam o catálogo.</li>
      <li>Claude Code: <code>claude mcp remove aegis</code> e adicione com outro nome, por exemplo <code>aegis-hub</code>. Ou <code>MCP_DISCOVERY_CACHE=0</code>.</li>
    </ol>
  </div>
  <p class="muted">Em produção a URL precisa ser HTTPS público (a nuvem da Anthropic acessa o servidor).</p>
</body>
</html>"""
    )
