from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EUR_PER_MILLION_TOKENS = {"gpt-5-mini": (0.22, 1.76)}
EUR_PER_SEMANTIC_QUERY = 1.76 / 1000


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    foundry_project_endpoint: str
    foundry_account_endpoint: str
    search_endpoint: str
    search_index: str
    chat_model: str
    embedding_model: str
    cosmos_endpoint: str
    cosmos_database: str = "juriscope"

    @field_validator("chat_model")
    @classmethod
    def priced(cls, model: str) -> str:
        if model not in EUR_PER_MILLION_TOKENS:
            raise ValueError(f"no price for {model}")
        return model


def cost_eur(model: str, usage: dict[str, int]) -> float:
    per_input, per_output = EUR_PER_MILLION_TOKENS[model]
    inputs = sum(n for key, n in usage.items() if key.endswith("_input"))
    outputs = sum(n for key, n in usage.items() if key.endswith("_output"))
    searches = usage.get("searches", 0) * EUR_PER_SEMANTIC_QUERY
    return round((inputs * per_input + outputs * per_output) / 1e6 + searches, 6)
