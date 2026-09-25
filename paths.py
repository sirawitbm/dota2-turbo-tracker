"""Where Turbo Tracker keeps its data.

- Running from source: the git-ignored `local/` folder next to the code.
- Portable exe (a `portable.flag` file beside it): `data/` beside the exe.
- Installed exe: %LOCALAPPDATA%\\TurboTracker.
"""

import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
HERE = Path(__file__).resolve().parent
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else HERE


def data_dir():
    override = os.environ.get("TURBO_TRACKER_DATA")   # demo / screenshots
    if override:
        return Path(override)
    if not FROZEN:
        return HERE / "local"
    if (APP_DIR / "portable.flag").exists():
        return APP_DIR / "data"
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "TurboTracker"


DATA = data_dir()

# Name for the single-instance mutex and the "show yourself" pipe. A demo
# or test run with its own data folder gets its own name, so it never
# talks to (or is blocked by) the copy the user is actually running.
INSTANCE = "TurboTracker"
if os.environ.get("TURBO_TRACKER_DATA"):
    import hashlib
    INSTANCE += "-" + hashlib.sha1(str(DATA).encode()).hexdigest()[:8]
SETTINGS = DATA / "settings.json"
DB_PATH = DATA / "turbo.db"
HEROES_CACHE = DATA / "heroes.json"
PORTRAITS = DATA / "portraits"
