# Turbo Tracker (Dota 2)

Read `PLAN.md` in this folder before doing anything - it is the full
handoff: what to build, in what order, what to verify first, and the rules.

In short:
- Phase 1: log Turbo matches from Dota 2 Game State Integration, show a
  recap card after each game. Start by capturing real GSI payloads from one
  game before designing the data model.
- Phase 2: backfill older Turbo matches from the OpenDota API, then stats.
- Use the `windows-game-overlay` skill for any window, tray or packaging
  work.
- The user (Jome) is a beginner: explain plainly, one step at a time.
- Set a repo-local git identity to the noreply address before the first
  commit (details in PLAN.md).
