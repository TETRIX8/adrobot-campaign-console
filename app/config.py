from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Adrobot Campaign Console"
    database_url: str = "sqlite:///./adrobot.db"
    keitaro_base_url: str = "https://tlgk.host"
    keitaro_api_key: str = ""
    keitaro_timeout_seconds: int = 20
    demo_mode: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def keitaro_api_url(self) -> str:
        return self.keitaro_base_url.rstrip("/") + "/admin_api/v1"

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url
        if url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+pymysql://", 1)
        elif url.startswith("mysql+mysqldb://"):
            url = url.replace("mysql+mysqldb://", "mysql+pymysql://", 1)
        if url.startswith("mysql+"):
            parts = urlsplit(url)
            query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key not in {"ssl", "ssl_ca", "ssl_cert", "ssl_key", "ssl_cipher"}]
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        return url

    @property
    def database_connect_args(self) -> dict:
        if not self.database_url.startswith("mysql"):
            return {"check_same_thread": False} if self.database_url.startswith("sqlite") else {}
        query = dict(parse_qsl(urlsplit(self.database_url).query, keep_blank_values=True))
        tls = query.get("ssl")
        if not tls:
            return {}
        try:
            options = json.loads(tls)
        except json.JSONDecodeError:
            options = {}
        return {"ssl": {"check_hostname": bool(options.get("rejectUnauthorized", True))}}

    @property
    def configured(self) -> bool:
        return bool(self.keitaro_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
