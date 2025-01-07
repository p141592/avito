from pydantic_settings import BaseSettings


class AVITOSettings(BaseSettings):
    AVITO_CLIENT_ID: str
    AVITO_SECRET: str
