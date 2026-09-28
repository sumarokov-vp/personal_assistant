from pydantic import BaseModel, ConfigDict, SecretStr


class TelegramCredentials(BaseModel):
    model_config = ConfigDict(frozen=True)

    session: SecretStr
    api_id: int
    api_hash: SecretStr
