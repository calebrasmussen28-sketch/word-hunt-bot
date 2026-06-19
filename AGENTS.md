# AGENTS.md

Guidance for AI agents working in this repository.

## Project overview

**word-hunt-bot** is a Python CLI that solves iMessage Word Hunt 4×4 boards and (on macOS) automates mouse drags through a QuickTime-mirrored iPhone window via Switch Control.

| File | Role |
|---|---|
| `main.py` | CLI entry: calibration, board input, orchestration |
| `solver.py` | Prefix-pruned DFS board solver (`WordHuntSolver`) |
| `controller.py` | pyautogui drag automation |
| `CSW24.txt` | Bundled English dictionary (~3 MB) |

There is no web server, Docker stack, test suite, or linter configuration.

## Branch note

`main` may contain only an initial README. The full implementation lives on `cursor/word-hunt-bot-1c0e` (or whichever feature branch is current). Check out that branch before developing or testing.

## Cursor Cloud specific instructions

### Dependencies

- **Python 3** (stdlib only for the solver; `pyautogui` for the full CLI).
- The VM update script installs `pyautogui` (`python3 -m pip install --break-system-packages pyautogui`), so it is already present in Cloud sessions.
- `controller.py` imports `pyautogui` inside a `try/except ImportError`, so the solver and `main.py --help` work even if `pyautogui` is missing. `pyautogui` is only loaded when the automation path runs.
- On **Linux**, importing `pyautogui` requires the **`python3-tk`** system package; this is baked into the VM snapshot (it is intentionally NOT in the update script, since it is a system dep).

### What can run in Cloud vs macOS

The Cloud VM has a live X display (`DISPLAY=:1`), so `pyautogui` imports and reports a real screen size, and mouse moves work.

| Mode | Cloud VM | macOS + iPhone |
|---|---|---|
| Solver-only (`WordHuntSolver` from `solver.py`) | Yes | Yes |
| `python3 main.py --help` | Yes (no extra deps) | Yes |
| `--dry-run` (solve + pixel-map, no real drags) | Yes — calibration reads the live cursor, so script it by moving the `pyautogui` cursor during the two 3s capture windows and piping board letters to stdin | Yes |
| Live playback against a real Word Hunt board | No (no QuickTime/iPhone/Switch Control) | Yes |

Full end-to-end automation against an actual game requires macOS, QuickTime Player (iPhone USB mirror), Switch Control, and Word Hunt on the device. The mouse-drag layer itself (`controller.py`) does run in the Cloud VM, but there is no game window to control.

### Verify the environment

Syntax check:

```bash
python3 -m py_compile main.py controller.py solver.py
```

Solver smoke test (core functionality):

```bash
python3 -c "
from solver import WordHuntSolver
s = WordHuntSolver('abcdefghijklmnop', 'CSW24.txt')
print(len(s.solve()), 'words found')
"
```

CLI help:

```bash
python3 main.py --help
```

### Running the bot (macOS)

See [README.md](README.md) for QuickTime calibration, dictionary options, `--dry-run`, and timing flags.
