from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração via variáveis de ambiente. NUNCA use valores reais como default em produção."""

    mongodb_uri: str = ""
    mongodb_db_name: str = "aegis"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    # Origens permitidas para CORS (separadas por vírgula). Ex: http://localhost:5173,https://app.exemplo.com
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # Email do primeiro admin (acesso à área admin mesmo sem is_admin no banco). Deixe vazio em prod após criar o admin.
    initial_admin_email: str = ""
    # Reset de senha
    password_reset_expire_minutes: int = 30
    # URL pública do frontend (link no email de reset)
    app_base_url: str = "http://localhost:5173"
    # SMTP genérico (email de reset de senha)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
