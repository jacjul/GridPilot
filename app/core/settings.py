from pydantic_settings import BaseSettings ,SettingsConfigDict
from pathlib import Path 
from enum import Enum
from typing import ClassVar

class SAMESITE(Enum):
    LAX = "lax"
    STRICT = "strict"
    NONE = "none"

class Settings(BaseSettings):
    path_env_file:ClassVar[Path] = Path(__file__).resolve().parent.parent / ".env"
    
    model_config = SettingsConfigDict(env_file=path_env_file, env_file_encoding="utf-8")

    ENV:str = "dev"

    DATABASE_URL:str
    REDIS_URL:str

    SECRET_KEY :str
    ALGORITHM : str

    ACCESS_TOKEN_MIN:int
    REFRESH_TOKEN_DAYS:int
    
    #refresh token default
    SECURE_COOKIE:bool= False
    SAMESITE_COOKIE:SAMESITE= SAMESITE.LAX

settings = Settings()
    