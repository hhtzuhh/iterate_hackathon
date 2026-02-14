from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    app_name: str = "blaxel-hello-world"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def frontend_dir(self) -> Path:
        return Path(__file__).parent.parent / "frontend"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
