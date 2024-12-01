import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    ENV: Literal["DEV", "PROD"] = "DEV"
    LEVEL: str = "INFO"

    API_ID: str = ""
    API_HASH: str = ""
    PHONE_NUMBER: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )
config = Config()