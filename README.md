# Turbo Tracker

**Your Dota 2 Turbo games, logged live.** Turbo Tracker records every game
you play, shows a recap card the moment a match ends, and keeps per-hero
stats - for a mode most stat sites barely cover.

![Turbo Tracker main window: stat tiles, and a list of recent Turbo matches with hero portraits](docs/main.png)

<img align="right" width="300" src="docs/recap.png" alt="Recap card: Victory as Pudge, 14/5/21, 3rd game on Pudge today">

When a game ends you get a card like this - result, K/D/A, GPM/XPM, how
many times you've played that hero today and your record on it.

It uses Valve's official **Game State Integration**: Dota itself sends your
own hero's stats to the app on your PC. Turbo Tracker never touches the
game - no input, no memory reading, nothing injected - so it is as safe as
any stats site.

<br clear="right">

## Download

Get the latest from **[Releases](https://github.com/sirawitbm/dota2-turbo-tracker/releases/latest)**:

| File | Pick it if |
| --- | --- |
| `TurboTracker-v0.1.0-Setup.exe` | You want a normal install with a Start menu entry. No admin needed. |
| `TurboTracker-v0.1.0-windows-x64.zip` | You want a portable copy. Unzip anywhere; data stays in a `data` folder beside the exe. |

Windows **SmartScreen will warn** ("Windows protected your PC") because the
app isn't code-signed. Click **More info > Run anyway**. To check the file
is the one built here, compare its SHA-256 with the `.sha256` file on the
release page:

```powershell
Get-FileHash .\TurboTracker-v0.1.0-Setup.exe -Algorithm SHA256
```

## Setup (once)

1. **Steam launch option.** In Steam, right-click **Dota 2 > Properties >
   General > Launch Options** and add:

   ```
   -gamestateintegration
   ```

   Since a March 2022 update, Dota only sends game data with this flag.
2. **Start Turbo Tracker** and click **Set up now** on the yellow banner.
   That writes one small file into Dota's config folder
   (`...\dota 2 beta\game\dota\cfg\gamestate_integration\`) telling Dota
   where to send data.
3. **Restart Dota** if it was open.

The banner disappears once data starts arriving.

## Using it

Leave Turbo Tracker running while you play. The top-right pill shows what
it sees: *Waiting for Dota*, *Dota is running*, or live **In game** stats.

![Heroes tab: games, win-loss, a win-rate bar and averages per hero](docs/heroes.png)

- **Tiles**: total games (and today), win-loss, win rate (and your last
  10), current streak.
- **Matches / Heroes**: every game, or your record on each hero.
- **All games / Turbo only**: filter the whole window.
- **Recap style**:
  - **Popup** - the card appears bottom-right and closes after 20 seconds
    (hover it to keep it open, click to close).
  - **Taskbar panel** - a small pill on the taskbar beside the clock with
    today's record, and live stats while you play. The recap opens above it
    and stays until clicked. Closing the main window keeps the panel; click
    it to reopen, right-click to quit.

    ![Taskbar panel: Today 3-2, Pudge W 14/5/21](docs/panel.png)
- **Show last recap** brings back the card for your latest game.

### How it knows a game was Turbo

Dota's data doesn't say which mode you're playing. So a few minutes after
each game, Turbo Tracker looks the match up on
[OpenDota](https://www.opendota.com) and fills in the mode - until then the
match says *Checking mode...*. Bot and lobby games aren't on OpenDota; after
a few hours of trying they become *Practice / lobby* and never count in
**Turbo only**.

## Known limitations

- **Only your own hero.** As a player, Dota only reports your stats - and
  Turbo Tracker won't try to get anything else.
- **Mode needs OpenDota.** Games only count as Turbo once OpenDota has
  them, which takes a few minutes and needs an internet connection.
- **Primary monitor only** for the popup and the taskbar panel, and the
  panel expects the taskbar at the bottom.
- **Not code-signed**, hence the SmartScreen warning.
- The recap appears after the game, so fullscreen is fine. There's no
  in-game overlay yet (that would need **borderless windowed**).
- No older games yet - importing your history from OpenDota is planned.

## Your data

Everything stays on your PC: in `%LOCALAPPDATA%\TurboTracker` for the
installed version, or the `data` folder beside a portable exe. The only
things sent anywhere are match ids to OpenDota (to look up the mode) and
downloads of hero names and pictures.

To uninstall completely, also delete
`gamestate_integration_turbotracker.cfg` from Dota's
`cfg\gamestate_integration` folder.

## Running from source

Needs Python 3.10+ and PySide6.

```
pip install -r requirements.txt
python turbo_tracker.py
```

- `python -m unittest discover tests` - tests.
- `capture.py` records raw Dota messages to `captures/`; `replay.py` plays
  one back into the running app - handy for testing without playing.
  Captures contain your Steam id; they're git-ignored.
- `tools/screenshots.py` regenerates `docs/` from made-up demo games.
- `.\release.ps1` builds the exe, zip and installer (needs Inno Setup 6).

## How this was made

AI-assisted: built with Claude as a coding agent - I decide what to build,
test it, and use it. Commits carry a `Co-Authored-By` trailer.

## License

MIT - see [LICENSE](LICENSE).
