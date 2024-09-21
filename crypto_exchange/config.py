import json
import os

from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path


class Config(BaseSettings):
    host: str | None = Field("0.0.0.0", env="HOST")
    port: int | None = Field(8080, env="PORT")
    redis_host: str | None = Field("localhost", env="REDIS_HOST")
    redis_port: int | None = Field(6379, env="REDIS_PORT")

    class Config:
        case_sensitive = False

    @classmethod
    def from_file(cls, file_path: str):
        config_path = Path(file_path)
        if not config_path.is_file():
            raise FileNotFoundError(
                f"Configuration file '{file_path}' not found."
            )

        with open(file_path, 'r') as f:
            config_data = json.load(f)

        return cls(**config_data)


config: Config | None = None


def get_config() -> Config:
    global config

    if not config:
        config = Config.from_file(os.environ.get(
            "CONFIG_PATH",
            "configs/dev.json"),
        )
    return config
