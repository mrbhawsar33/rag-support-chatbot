from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str
    debug: bool
    database_url: str
    upload_dir: str

    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()