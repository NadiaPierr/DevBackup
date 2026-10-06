"""Resolve application data paths for development and installed usage."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_path, user_documents_path


APP_NAME = "DevProjectBackup"
DEVELOPMENT_ENV_VAR = "DEV_BACKUP_ENV"


def is_development() -> bool:
    """Return whether local development storage has been explicitly enabled."""
    return os.getenv(DEVELOPMENT_ENV_VAR, "").strip().casefold() == "development"


def get_data_dir() -> Path:
    """Return .devdata in development, otherwise the OS-specific local data dir."""
    if is_development():
        return Path(__file__).resolve().parent.parent / ".devdata"
    # appauthor=False prevents an unnecessary Publisher/AppName nesting on Windows.
    return user_data_path(APP_NAME, appauthor=False, roaming=False)


def get_default_backup_root() -> Path:
    """Return a visible default location for archives created by the user."""
    if is_development():
        return Path(__file__).resolve().parent.parent / ".devdata" / "archives"
    return user_documents_path() / "DevProjectBackups"
