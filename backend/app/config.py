from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração via variáveis de ambiente. NUNCA use valores reais como default em produção."""

    mongodb_uri: str = ""
    mongodb_db_name: str = "valorian4future"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    # Origens permitidas para CORS (separadas por vírgula). Ex: http://localhost:5173,https://app.exemplo.com
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # Email do primeiro admin (acesso à área admin mesmo sem is_admin no banco). Deixe vazio em prod após criar o admin.
    initial_admin_email: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
