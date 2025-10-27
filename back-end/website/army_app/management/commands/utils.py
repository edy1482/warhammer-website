from pathlib import Path

def get_version_folders(base_dir):
    """
    Returns sorted list of timestamped version folders in ascending order.
    """
    base_dir = Path(base_dir)
    folders = [f for f in base_dir.iterdir() if f.is_dir() and f.name != "__pycache__"]
    return sorted(folders, key=lambda x: x.name)

def get_latest_version(base_dir):
    """
    Returns the latest version folder or None if none exist.
    """
    folders = get_version_folders(base_dir)
    return folders[-1] if folders else None

def get_previous_version(base_dir):
    """
    Returns the previous version (second-to-latest) if exists.
    """
    folders = get_version_folders(base_dir)
    return folders[-2] if len(folders) > 1 else None