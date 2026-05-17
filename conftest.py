"""Root conftest — required by pytest-homeassistant-custom-component."""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so that custom_components is importable
# as a plain namespace package without any editable-install path hooks.
_PROJECT_ROOT = str(Path(__file__).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Setuptools editable installs add a synthetic path hook entry to namespace packages
# that is not a real directory. HA's integration loader calls os.listdir() on every
# __path__ entry, which raises FileNotFoundError for synthetic entries.
import custom_components  # noqa: E402

custom_components.__path__ = [
    p for p in custom_components.__path__ if Path(p).is_dir()
]

pytest_plugins = "pytest_homeassistant_custom_component"
