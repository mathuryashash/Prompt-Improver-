import tomllib
from dataclasses import dataclass

from core.paths import get_user_data_path

CONFIG_PATH = get_user_data_path("config.toml")


@dataclass
class Config:
    hotkey: str
    backend: str
    host: str
    model_name: str
    timeout: int
    persona_role: str
    persona_domain: str
    persona_style: str
    learning_enabled: bool
    min_samples: int
    history_days_to_keep: int
    startup_with_windows: bool
    pause_on_start: bool
    temperature: float


def load_config() -> Config:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.toml not found at {CONFIG_PATH}. "
            "Copy config.example.toml to config.toml and edit it."
        )
    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)
    return Config(
        hotkey=raw["app"]["hotkey"],
        backend=raw["model"]["backend"],
        host=raw["model"]["host"],
        model_name=raw["model"]["model_name"],
        timeout=raw["model"]["timeout_seconds"],
        persona_role=raw["persona"]["role"],
        persona_domain=raw["persona"]["domain"],
        persona_style=raw["persona"]["style"],
        learning_enabled=raw["learning"]["enabled"],
        min_samples=raw["learning"]["min_samples_before_adapting"],
        history_days_to_keep=raw["learning"].get("history_days_to_keep", 90),
        startup_with_windows=raw["app"].get("startup_with_windows", False),
        pause_on_start=raw["app"].get("pause_on_start", False),
        temperature=raw["model"].get("temperature", 0.4),
    )
