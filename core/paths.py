import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to read-only resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent.parent / relative_path


def get_user_data_path(relative_path: str) -> Path:
    """Get path to user-writable files (config, database)."""
    if getattr(sys, 'frozen', False):
        # When running as an EXE, put user data in the directory containing the EXE
        return Path(sys.executable).parent / relative_path
    return Path(__file__).parent.parent / relative_path
