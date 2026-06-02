"""CLI orchestrator for the QuickTime/Switch Control Word Hunt bot."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from controller import (
    DEFAULT_DRAG_POINT_DURATION_SECONDS,
    DEFAULT_WORD_SETTLE_SECONDS,
    AutomationError,
    PixelCoordinate,
    execute_drag_paths,
    require_pyautogui,
)
from solver import (
    BOARD_SIZE,
    BOARD_TILE_COUNT,
    DEFAULT_MIN_WORD_LENGTH,
    Coordinate,
    CoordinatePath,
    WordHuntSolver,
    WordHuntSolverError,
)


CoordinatePixelLookup = Dict[Coordinate, PixelCoordinate]
PixelPath = List[PixelCoordinate]

DEFAULT_DICTIONARY_FILENAMES = (
    "dictionary.txt",
    "words.txt",
)
SYSTEM_DICTIONARY_PATHS = (
    "/usr/share/dict/words",
)


class CalibrationError(Exception):
    """Raised when board-to-screen calibration is invalid."""


class MainConfigurationError(Exception):
    """Raised when the CLI cannot determine a required configuration value."""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Solve and play iMessage Word Hunt through a QuickTime mirrored "
            "iPhone window using pyautogui mouse drags."
        )
    )
    parser.add_argument(
        "--dictionary",
        help=(
            "Path to a local newline-delimited English dictionary. If omitted, "
            "WORD_HUNT_DICTIONARY, ./dictionary.txt, ./words.txt, then "
            "/usr/share/dict/words are checked."
        ),
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=DEFAULT_MIN_WORD_LENGTH,
        help="Minimum word length to submit. Defaults to 3.",
    )
    parser.add_argument(
        "--max-words",
        type=int,
        help="Optional cap on how many longest-first words to play.",
    )
    parser.add_argument(
        "--drag-duration",
        type=float,
        default=DEFAULT_DRAG_POINT_DURATION_SECONDS,
        help=(
            "Seconds spent moving between adjacent letter centers. Defaults to "
            f"{DEFAULT_DRAG_POINT_DURATION_SECONDS}."
        ),
    )
    parser.add_argument(
        "--word-delay",
        type=float,
        default=DEFAULT_WORD_SETTLE_SECONDS,
        help=(
            "Seconds to pause after each completed word for Switch Control. "
            f"Defaults to {DEFAULT_WORD_SETTLE_SECONDS}."
        ),
    )
    parser.add_argument(
        "--start-delay",
        type=float,
        default=1.0,
        help="Seconds to wait after solving before the first automated drag.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solve and print mapped paths without moving the mouse.",
    )
    return parser.parse_args(argv)


def resolve_dictionary_path(cli_dictionary_path: Optional[str]) -> str:
    if cli_dictionary_path:
        return _validate_dictionary_path(cli_dictionary_path, source="--dictionary")

    env_dictionary_path = os.environ.get("WORD_HUNT_DICTIONARY")
    if env_dictionary_path:
        return _validate_dictionary_path(env_dictionary_path, source="WORD_HUNT_DICTIONARY")

    candidates = [
        str(Path.cwd() / filename) for filename in DEFAULT_DICTIONARY_FILENAMES
    ]
    candidates.extend(SYSTEM_DICTIONARY_PATHS)

    for candidate in candidates:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.is_file():
            return str(candidate_path)

    raise MainConfigurationError(
        "No dictionary file found. Provide --dictionary /path/to/words.txt or "
        "set WORD_HUNT_DICTIONARY. Checked: " + ", ".join(candidates)
    )


def run_calibration() -> CoordinatePixelLookup:
    pyautogui = require_pyautogui()

    print("\nCalibration uses the live QuickTime Player mirrored iPhone window.")
    print("Keep the Word Hunt board visible and avoid resizing the window after calibration.\n")

    top_left = capture_calibration_point(
        pyautogui=pyautogui,
        prompt=(
            "Hover your mouse over the CENTER of the TOP-LEFT letter tile. "
            "Capturing in 3 seconds..."
        ),
    )
    bottom_right = capture_calibration_point(
        pyautogui=pyautogui,
        prompt=(
            "Hover your mouse over the CENTER of the BOTTOM-RIGHT letter tile. "
            "Capturing in 3 seconds..."
        ),
    )

    lookup = build_coordinate_pixel_lookup(top_left, bottom_right)
    print("\nCalibrated 4x4 pixel lookup table:")
    print(format_pixel_lookup(lookup))
    return lookup


def capture_calibration_point(pyautogui, prompt: str) -> PixelCoordinate:
    print(prompt)
    time.sleep(3)
    position = pyautogui.position()
    coordinate = (int(position.x), int(position.y))
    print(f"Captured cursor location: {coordinate}")
    return coordinate


def build_coordinate_pixel_lookup(
    top_left: PixelCoordinate,
    bottom_right: PixelCoordinate,
) -> CoordinatePixelLookup:
    start_x, start_y = top_left
    end_x, end_y = bottom_right

    if end_x <= start_x or end_y <= start_y:
        raise CalibrationError(
            "Bottom-right calibration point must be down and right of the top-left point. "
            f"Received top-left={top_left}, bottom-right={bottom_right}."
        )

    step_x = (end_x - start_x) / float(BOARD_SIZE - 1)
    step_y = (end_y - start_y) / float(BOARD_SIZE - 1)

    lookup: CoordinatePixelLookup = {}
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            lookup[(row, col)] = (
                int(round(start_x + (col * step_x))),
                int(round(start_y + (row * step_y))),
            )

    return lookup


def format_pixel_lookup(lookup: CoordinatePixelLookup) -> str:
    rows: List[str] = []
    for row in range(BOARD_SIZE):
        row_values = [str(lookup[(row, col)]) for col in range(BOARD_SIZE)]
        rows.append("  " + "  ".join(row_values))
    return "\n".join(rows)


def map_coordinate_path_to_pixels(
    coordinate_path: CoordinatePath,
    lookup: CoordinatePixelLookup,
) -> PixelPath:
    pixel_path: PixelPath = []

    for coordinate in coordinate_path:
        if coordinate not in lookup:
            raise CalibrationError(f"Path contains out-of-board coordinate: {coordinate}")
        pixel_path.append(lookup[coordinate])

    return pixel_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    try:
        dictionary_path = resolve_dictionary_path(args.dictionary)
        validate_runtime_args(args)
    except MainConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    print(f"Using dictionary: {dictionary_path}")

    try:
        lookup = run_calibration()
    except (AutomationError, CalibrationError) as exc:
        print(f"Calibration failed: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCalibration cancelled.")
        return 130

    print(
        "\nEnter the board letters row-by-row as a 16-character string "
        f"(example: ABCDEFGHIJKLMNOP). Type 'q' to quit.\n"
    )

    while True:
        try:
            raw_letters = input("Word Hunt board letters> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nExiting.")
            return 130

        if raw_letters.lower() in {"q", "quit", "exit"}:
            return 0
        if not raw_letters:
            continue

        try:
            play_board(
                letters=raw_letters,
                dictionary_path=dictionary_path,
                lookup=lookup,
                min_word_length=args.min_length,
                max_words=args.max_words,
                drag_duration_seconds=args.drag_duration,
                word_delay_seconds=args.word_delay,
                start_delay_seconds=args.start_delay,
                dry_run=args.dry_run,
            )
        except KeyboardInterrupt:
            print("\nPlayback interrupted.")
            return 130
        except (WordHuntSolverError, AutomationError, CalibrationError) as exc:
            print(f"Error: {exc}", file=sys.stderr)


def validate_runtime_args(args: argparse.Namespace) -> None:
    if args.min_length < 1 or args.min_length > BOARD_TILE_COUNT:
        raise MainConfigurationError(
            f"--min-length must be between 1 and {BOARD_TILE_COUNT}."
        )
    if args.max_words is not None and args.max_words < 1:
        raise MainConfigurationError("--max-words must be at least 1 when provided.")
    if args.drag_duration < 0:
        raise MainConfigurationError("--drag-duration must be non-negative.")
    if args.word_delay < 0:
        raise MainConfigurationError("--word-delay must be non-negative.")
    if args.start_delay < 0:
        raise MainConfigurationError("--start-delay must be non-negative.")


def play_board(
    letters: str,
    dictionary_path: str,
    lookup: CoordinatePixelLookup,
    min_word_length: int,
    max_words: Optional[int],
    drag_duration_seconds: float,
    word_delay_seconds: float,
    start_delay_seconds: float,
    dry_run: bool,
) -> None:
    solver = WordHuntSolver(
        letters=letters,
        dictionary_path=dictionary_path,
        min_word_length=min_word_length,
    )
    solved_words = solver.solve()

    if not solved_words:
        print("No valid words found for this board.")
        return

    selected_words = solved_words[:max_words] if max_words is not None else solved_words
    pixel_paths = [
        map_coordinate_path_to_pixels(path, lookup) for _, path in selected_words
    ]

    print(
        f"Found {len(solved_words)} words; "
        f"{len(selected_words)} will be {'printed' if dry_run else 'played'}."
    )
    print_solution_preview(selected_words)

    if dry_run:
        print("\nDry run pixel paths:")
        for (word, _), pixel_path in zip(selected_words, pixel_paths):
            print(f"  {word}: {pixel_path}")
        return

    print(
        f"\nStarting automated playback in {start_delay_seconds:.2f}s. "
        "Move the mouse to the top-left screen corner to trigger pyautogui fail-safe."
    )
    time.sleep(start_delay_seconds)

    executed_count = execute_drag_paths(
        pixel_paths,
        drag_point_duration_seconds=drag_duration_seconds,
        word_settle_seconds=word_delay_seconds,
    )
    print(f"Completed {executed_count} word drag paths.")


def print_solution_preview(
    solved_words: Sequence[Tuple[str, CoordinatePath]],
    preview_limit: int = 20,
) -> None:
    print("\nLongest-first solution preview:")
    for word, path in solved_words[:preview_limit]:
        print(f"  {word:<16} {path}")
    if len(solved_words) > preview_limit:
        print(f"  ... {len(solved_words) - preview_limit} more")


def _validate_dictionary_path(raw_path: str, source: str) -> str:
    path = Path(raw_path).expanduser()
    if not path.exists():
        raise MainConfigurationError(f"{source} path does not exist: {path}")
    if not path.is_file():
        raise MainConfigurationError(f"{source} path is not a file: {path}")
    return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
