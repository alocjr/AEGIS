import html


# Paleta inspirada em frontend-vue/public/lp.html
_NAVY_DEEP = "#0C1827"
_NAVY = "#14213A"
_NAVY_MID = "#1B2D4F"
_GOLD = "#B8962E"
_GOLD_LIGHT = "#D4AF55"
_IVORY = "#F4F1EB"
_TEXT = "#2A3548"
_MUTED = "#6B7E9A"
_BORDER = "rgba(184, 150, 46, 0.22)"


def render_password_reset_html(reset_link: str, token: str, expire_minutes: int) -> str:
    """HTML de email transacional (tabelas + estilos inline para clientes de email)."""
    safe_link = html.escape(reset_link, quote=True)
    safe_token = html.escape(token)
    safe_expire = html.escape(str(expire_minutes))

    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Recuperação de senha</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
</head>
<body style="margin:0;padding:0;background-color:{_NAVY_DEEP};font-family:Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:{_NAVY_DEEP};">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background-color:{_IVORY};border:1px solid {_BORDER};border-radius:2px;overflow:hidden;">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,{_NAVY_DEEP} 0%,{_NAVY_MID} 100%);padding:28px 32px;border-bottom:1px solid {_BORDER};">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td width="44" valign="middle" style="padding-right:14px;">
                    <div style="width:40px;height:40px;background-color:{_NAVY_DEEP};border:1px solid {_GOLD};border-radius:4px;text-align:center;line-height:40px;font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:bold;color:{_GOLD_LIGHT};">V</div>
                  </td>
                  <td valign="middle">
                    <div style="font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:600;letter-spacing:0.2em;text-transform:uppercase;color:{_GOLD};margin-bottom:4px;">Valorian</div>
                    <div style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:300;line-height:1.2;color:{_IVORY};">
                      4 <span style="color:{_GOLD_LIGHT};">Future</span>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Eyebrow -->
          <tr>
            <td style="padding:32px 32px 0;">
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:600;letter-spacing:0.22em;text-transform:uppercase;color:{_GOLD};">
                Segurança da conta
              </p>
            </td>
          </tr>
          <!-- Title -->
          <tr>
            <td style="padding:12px 32px 0;">
              <h1 style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:28px;font-weight:400;line-height:1.2;color:{_TEXT};">
                Redefinir sua senha
              </h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:16px 32px 0;">
              <p style="margin:0 0 16px;font-size:15px;line-height:1.65;color:{_TEXT};">
                Recebemos uma solicitação para redefinir a senha da sua conta na plataforma
                <strong style="font-weight:600;">Valorian 4 Future</strong>.
              </p>
              <p style="margin:0 0 24px;font-size:15px;line-height:1.65;color:{_MUTED};">
                O link abaixo é válido por <strong style="color:{_TEXT};font-weight:600;">{safe_expire} minutos</strong>.
                Após esse prazo, será necessário solicitar um novo reset.
              </p>
            </td>
          </tr>
          <!-- CTA -->
          <tr>
            <td align="center" style="padding:8px 32px 28px;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="center" style="border-radius:2px;background-color:{_GOLD};">
                    <a href="{safe_link}" target="_blank" style="display:inline-block;padding:14px 32px;font-family:Arial,Helvetica,sans-serif;font-size:13px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:{_NAVY_DEEP};text-decoration:none;">
                      Redefinir senha
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Fallback link -->
          <tr>
            <td style="padding:0 32px 24px;">
              <p style="margin:0 0 8px;font-size:12px;line-height:1.5;color:{_MUTED};">
                Se o botão não funcionar, copie e cole este endereço no navegador:
              </p>
              <p style="margin:0;word-break:break-all;font-size:12px;line-height:1.5;">
                <a href="{safe_link}" style="color:{_NAVY};text-decoration:underline;">{safe_link}</a>
              </p>
            </td>
          </tr>
          <!-- Token box -->
          <tr>
            <td style="padding:0 32px 32px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#EBE7DF;border:1px dashed {_BORDER};border-radius:4px;">
                <tr>
                  <td style="padding:16px 18px;">
                    <p style="margin:0 0 8px;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:{_MUTED};">
                      Token alternativo
                    </p>
                    <p style="margin:0 0 6px;font-size:13px;line-height:1.5;color:{_TEXT};">
                      Na tela de login, escolha <em>Nova senha</em> e informe o token:
                    </p>
                    <p style="margin:0;font-family:Consolas,'Courier New',monospace;font-size:12px;line-height:1.5;word-break:break-all;color:{_NAVY};background-color:{_IVORY};padding:10px 12px;border-radius:3px;border:1px solid {_BORDER};">
                      {safe_token}
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Divider -->
          <tr>
            <td style="padding:0 32px;">
              <hr style="border:none;border-top:1px solid #E0DBD2;margin:0;">
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:24px 32px 28px;">
              <p style="margin:0 0 12px;font-size:13px;line-height:1.6;color:{_MUTED};">
                Se você <strong style="color:{_TEXT};">não solicitou</strong> esta alteração, ignore este email.
                Sua senha permanecerá a mesma.
              </p>
              <p style="margin:0;font-size:11px;line-height:1.5;color:#9AA8BC;">
                © Valorian 4 Future · AI Executive Mentoring<br>
                Este é um email automático; por favor, não responda.
              </p>
            </td>
          </tr>
        </table>
        <!-- Outer footer -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
          <tr>
            <td align="center" style="padding:20px 16px 0;">
              <p style="margin:0;font-size:11px;color:#8A9BB5;line-height:1.5;">
                Mentoria executiva em Inteligência Artificial
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_password_reset_text(reset_link: str, token: str, expire_minutes: int) -> str:
    return (
        "VALORIAN 4 FUTURE — Recuperação de senha\n"
        "========================================\n\n"
        "Recebemos uma solicitação para redefinir a senha da sua conta.\n\n"
        f"Redefinir senha (válido por {expire_minutes} minutos):\n"
        f"{reset_link}\n\n"
        "Token alternativo (tela Nova senha):\n"
        f"{token}\n\n"
        "Se você não solicitou esta alteração, ignore este email.\n"
        "— Valorian 4 Future · AI Executive Mentoring\n"
    )
