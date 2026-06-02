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
- Install runtime dependency: `python3 -m pip install pyautogui` (see README).
- On **Linux**, `main.py` imports `controller.py`, which loads pyautogui/MouseInfo and requires **`python3-tk`**. This is a one-time system package (`sudo apt-get install python3-tk`); it is not in the VM update script.

### What can run in Cloud vs macOS

| Mode | Cloud VM | macOS + iPhone |
|---|---|---|
| Solver-only (`WordHuntSolver` from `solver.py`) | Yes | Yes |
| `python3 main.py --help` | Yes (with `python3-tk`) | Yes |
| `--dry-run` / live playback | No (needs interactive calibration + display) | Yes |

Full end-to-end automation requires macOS, QuickTime Player (iPhone USB mirror), Switch Control, and Word Hunt on the device. Do not expect mouse automation tests to pass in Linux Cloud VMs.

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
