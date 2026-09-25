"""One-time setup: tell Dota 2 to send game data to Turbo Tracker.

Writes gamestate_integration_turbotracker.cfg into Dota's cfg folder and
keeps the secret token in local/settings.json (git-ignored).

Run:  python setup_gsi.py
"""

import json
import secrets
import sys
import winreg
from pathlib import Path

from paths import SETTINGS

PORT = 3131  # Logitech already uses 3002
CFG_NAME = "gamestate_integration_turbotracker.cfg"

CFG_TEMPLATE = """"Turbo Tracker"
{{
	"uri"       "http://127.0.0.1:{port}/"
	"timeout"   "5.0"
	"buffer"    "0.1"
	"throttle"  "0.1"
	"heartbeat" "30.0"
	"auth"
	{{
		"token" "{token}"
	}}
	"data"
	{{
		"provider"  "1"
		"map"       "1"
		"player"    "1"
		"hero"      "1"
		"abilities" "1"
		"items"     "1"
		"buildings" "1"
		"draft"     "1"
		"events"    "1"
	}}
}}
"""


def steam_libraries():
    """Every Steam library folder on this PC."""
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
    steam = Path(winreg.QueryValueEx(key, "SteamPath")[0])
    libs = [steam]
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        for line in vdf.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split('"')
            if len(parts) >= 4 and parts[1] == "path":
                libs.append(Path(parts[3].replace("\\\\", "\\")))
    return libs


def find_dota_cfg():
    for lib in steam_libraries():
        cfg = lib / "steamapps" / "common" / "dota 2 beta" / "game" / "dota" / "cfg"
        if cfg.is_dir():
            return cfg
    return None


def load_settings():
    if SETTINGS.exists():
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    return {}


def config_path():
    """Where our GSI config goes, or None if Dota isn't found."""
    cfg_dir = find_dota_cfg()
    if cfg_dir is None:
        return None
    return cfg_dir / "gamestate_integration" / CFG_NAME


def launch_option_set():
    """True/False if we can tell from Steam's files, None if we can't.

    Steam keeps each game's launch options in userdata/<id>/config/
    localconfig.vdf. We only look for the flag; nothing is changed.
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam = Path(winreg.QueryValueEx(key, "SteamPath")[0])
    except OSError:
        return None
    files = list((steam / "userdata").glob("*/config/localconfig.vdf"))
    if not files:
        return None
    for f in files:
        try:
            if "-gamestateintegration" in f.read_text(encoding="utf-8",
                                                      errors="ignore"):
                return True
        except OSError:
            continue
    return False


def ensure_settings():
    settings = load_settings()
    settings.setdefault("token", secrets.token_urlsafe(24))
    settings.setdefault("port", PORT)
    settings.setdefault("recap_mode", "popup")  # "popup" or "panel"
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings


def config_matches():
    """True if our config file is there and carries this copy's token.

    Source runs and the exe keep separate settings, each with its own
    token. If the file on disk holds another copy's token, Dota's messages
    get rejected (403) and nothing ever shows up - so check the token, not
    just that the file exists.
    """
    target = config_path()
    if target is None or not target.exists():
        return False
    settings = load_settings()
    if not settings.get("token"):
        return False
    expected = CFG_TEMPLATE.format(port=settings.get("port", PORT),
                                   token=settings["token"])
    try:
        return target.read_text(encoding="utf-8", errors="ignore") == expected
    except OSError:
        return False


def install():
    """Write the config. Returns its path; raises RuntimeError on failure."""
    target = config_path()
    if target is None:
        raise RuntimeError("Could not find Dota 2. Is it installed through "
                           "Steam?")
    settings = ensure_settings()
    target.parent.mkdir(exist_ok=True)
    text = CFG_TEMPLATE.format(port=settings["port"], token=settings["token"])
    try:
        target.write_text(text, encoding="utf-8")
    except PermissionError:
        raise RuntimeError(f"Windows blocked writing to:\n  {target}\n"
                           "Run this again as administrator.") from None
    return target


def main():
    try:
        target = install()
    except RuntimeError as err:
        sys.exit(str(err))
    settings = load_settings()
    print(f"Wrote {target}")
    print(f"Listener port: {settings['port']}")
    print("Remember: Dota needs the launch option  -gamestateintegration")


if __name__ == "__main__":
    main()
