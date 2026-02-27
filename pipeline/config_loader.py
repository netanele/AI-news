"""Load and validate pipeline configuration from config.json."""

import json
import logging

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {
    "ai.provider": ("ai", "provider"),
    "ai.model": ("ai", "model"),
    "ai.apiKeyEnvVar": ("ai", "apiKeyEnvVar"),
    "display.daysToShow": ("display", "daysToShow"),
    "channels": ("channels",),
}


def load_config(config_path="config.json"):
    """Load and validate config.json. Returns parsed config dict."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    for key_name, path in REQUIRED_KEYS.items():
        obj = config
        for part in path:
            if not isinstance(obj, dict) or part not in obj:
                raise ValueError(f"Missing required config key: {key_name}")
            obj = obj[part]

    if not isinstance(config["channels"], list) or len(config["channels"]) == 0:
        raise ValueError("Config 'channels' must be a non-empty list")

    if not isinstance(config["display"]["daysToShow"], int) or config["display"]["daysToShow"] < 1:
        raise ValueError("Config 'display.daysToShow' must be a positive integer")

    # Deduplicate channels while preserving order
    seen = set()
    unique_channels = []
    for ch in config["channels"]:
        if ch not in seen:
            seen.add(ch)
            unique_channels.append(ch)
        else:
            logger.warning("Duplicate channel URL removed: %s", ch)
    config["channels"] = unique_channels

    logger.info("Config loaded: %d channels, %d days window", len(config["channels"]), config["display"]["daysToShow"])
    return config
