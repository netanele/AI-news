"""Tests for config_loader module."""

import json
import os
import tempfile

import pytest

from pipeline.config_loader import load_config


def _write_config(data):
    """Write a config dict to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


def _valid_config(**overrides):
    base = {
        "ai": {"provider": "gemini", "model": "gemini-2.0-flash", "apiKeyEnvVar": "GEMINI_API_KEY"},
        "display": {"daysToShow": 7},
        "channels": ["https://www.youtube.com/@Test"],
    }
    base.update(overrides)
    return base


class TestLoadConfig:
    def test_loads_valid_config(self):
        path = _write_config(_valid_config())
        try:
            config = load_config(path)
            assert config["ai"]["model"] == "gemini-2.0-flash"
            assert len(config["channels"]) == 1
        finally:
            os.unlink(path)

    def test_missing_ai_key_raises(self):
        data = _valid_config()
        del data["ai"]["model"]
        path = _write_config(data)
        try:
            with pytest.raises(ValueError, match="ai.model"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_empty_channels_raises(self):
        path = _write_config(_valid_config(channels=[]))
        try:
            with pytest.raises(ValueError, match="channels"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_negative_days_raises(self):
        data = _valid_config()
        data["display"]["daysToShow"] = -1
        path = _write_config(data)
        try:
            with pytest.raises(ValueError, match="daysToShow"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_deduplicates_channels(self):
        data = _valid_config(channels=[
            "https://www.youtube.com/@Test",
            "https://www.youtube.com/@Test",
            "https://www.youtube.com/@Other",
        ])
        path = _write_config(data)
        try:
            config = load_config(path)
            assert len(config["channels"]) == 2
        finally:
            os.unlink(path)

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.json")
