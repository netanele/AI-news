"""Write final data.json output — the atomic write point of the pipeline."""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def write_data(data, output_path="data.json"):
    """Write the final data structure to data.json atomically.

    Writes to a temp file first, then uses os.replace() for an atomic rename.
    This prevents data corruption if the process is killed mid-write.
    """
    data["lastUpdated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    dir_name = os.path.dirname(os.path.abspath(output_path))
    fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=dir_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, output_path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    logger.info("Wrote %s (last updated: %s)", output_path, data["lastUpdated"])
