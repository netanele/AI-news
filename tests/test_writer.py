"""Tests for writer module."""

import json
import os
import tempfile

from pipeline.writer import write_data


class TestWriteData:
    def test_writes_valid_json(self):
        data = {"days": [], "config": {"daysToShow": 7}}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            write_data(data, path)
            with open(path, "r") as f:
                result = json.load(f)
            assert "lastUpdated" in result
            assert result["days"] == []
        finally:
            os.unlink(path)

    def test_sets_last_updated_timestamp(self):
        data = {"days": []}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            write_data(data, path)
            with open(path, "r") as f:
                result = json.load(f)
            assert result["lastUpdated"].endswith("Z")
            assert "T" in result["lastUpdated"]
        finally:
            os.unlink(path)

    def test_atomic_write_no_partial_on_error(self):
        """Verify that if writing fails, the original file is preserved."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"original": true}')
            path = f.name
        try:
            # Try to write non-serializable data — should raise
            bad_data = {"days": [], "bad": object()}
            try:
                write_data(bad_data, path)
            except TypeError:
                pass
            # Original file should still be intact
            with open(path, "r") as f:
                content = f.read()
            assert "original" in content
        finally:
            os.unlink(path)

    def test_preserves_unicode(self):
        data = {"days": [], "summary": "bullet \u2022 point"}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            write_data(data, path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "\u2022" in content
        finally:
            os.unlink(path)
