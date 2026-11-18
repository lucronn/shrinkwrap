"""Location of ShrinkWrap's local buffer and analytics files."""

import os
from pathlib import Path


def state_dir() -> Path:
    configured = os.getenv("SHRINKWRAP_STATE_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".shrinkwrap"
