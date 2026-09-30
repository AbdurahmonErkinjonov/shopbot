from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_LOGIN: str
    ADMIN_PASSWORD: str
    ADMIN_ID: Union[int, str] = 0
    DATABASE_URL: str = "sqlite+aiosqlite:///bot.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def admin_ids(self) -> List[int]:
        if isinstance(self.ADMIN_ID, int):
            return [self.ADMIN_ID] if self.ADMIN_ID != 0 else []
        if isinstance(self.ADMIN_ID, str):
            return [int(x.strip()) for x in self.ADMIN_ID.split(",") if x.strip().isdigit()]
        return []


config = Settings()
