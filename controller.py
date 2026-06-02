"""Desktop mouse automation for playing Word Hunt through QuickTime.

This module drives the host Mac cursor with pyautogui. The cursor should be
aimed at the QuickTime Player movie recording window that mirrors the iPhone,
with Switch Control forwarding the gesture to the device.
"""

from __future__ import annotations

import time
from typing import List, Optional, Sequence, Tuple


PixelCoordinate = Tuple[int, int]

PYAUTOGUI_PAUSE_SECONDS = 0.01
DEFAULT_DRAG_POINT_DURATION_SECONDS = 0.025
DEFAULT_WORD_SETTLE_SECONDS = 0.05


class AutomationError(Exception):
    """Raised when desktop input automation cannot be completed."""


try:
    import pyautogui as _pyautogui
except ImportError:  # pragma: no cover - depends on local desktop environment.
    _pyautogui = None


if _pyautogui is not None:
    _pyautogui.PAUSE = PYAUTOGUI_PAUSE_SECONDS
    _pyautogui.MINIMUM_DURATION = 0.0


def require_pyautogui():
    """Return the pyautogui module or raise an actionable runtime error."""

    if _pyautogui is None:
        raise AutomationError(
            "pyautogui is not installed. Install it with `python -m pip install "
            "pyautogui` on the Mac that will control the QuickTime window."
        )
    return _pyautogui


def execute_drag_path(
    pixel_coordinates: Sequence[PixelCoordinate],
    drag_point_duration_seconds: float = DEFAULT_DRAG_POINT_DURATION_SECONDS,
    word_settle_seconds: float = DEFAULT_WORD_SETTLE_SECONDS,
) -> None:
    """Execute one Word Hunt swipe gesture across screen pixel coordinates.

    Args:
        pixel_coordinates: Ordered desktop pixel centers for the word path.
        drag_point_duration_seconds: Fast linear movement duration between
            adjacent tile centers.
        word_settle_seconds: Small delay after mouse-up to let Switch Control
            and the mirrored iPhone register the completed gesture.
    """

    coordinates = _normalize_pixel_coordinates(pixel_coordinates)
    if not coordinates:
        raise AutomationError("Cannot execute an empty drag path.")

    if drag_point_duration_seconds < 0:
        raise AutomationError("drag_point_duration_seconds must be non-negative.")
    if word_settle_seconds < 0:
        raise AutomationError("word_settle_seconds must be non-negative.")

    pyautogui = require_pyautogui()
    mouse_is_down = False

    try:
        first_x, first_y = coordinates[0]
        pyautogui.moveTo(first_x, first_y, duration=0)
        pyautogui.mouseDown()
        mouse_is_down = True

        for next_x, next_y in coordinates[1:]:
            pyautogui.moveTo(
                next_x,
                next_y,
                duration=drag_point_duration_seconds,
                tween=pyautogui.linear,
            )
    except Exception as exc:
        raise AutomationError(f"Failed while executing drag path: {exc}") from exc
    finally:
        if mouse_is_down:
            try:
                pyautogui.mouseUp()
            except Exception:
                pass

    time.sleep(word_settle_seconds)


def execute_drag_paths(
    pixel_paths: Sequence[Sequence[PixelCoordinate]],
    drag_point_duration_seconds: float = DEFAULT_DRAG_POINT_DURATION_SECONDS,
    word_settle_seconds: float = DEFAULT_WORD_SETTLE_SECONDS,
    max_paths: Optional[int] = None,
) -> int:
    """Execute multiple word paths and return the number attempted."""

    if max_paths is not None and max_paths < 1:
        raise AutomationError("max_paths must be at least 1 when provided.")

    executed_count = 0
    for pixel_path in pixel_paths:
        if max_paths is not None and executed_count >= max_paths:
            break
        execute_drag_path(
            pixel_path,
            drag_point_duration_seconds=drag_point_duration_seconds,
            word_settle_seconds=word_settle_seconds,
        )
        executed_count += 1

    return executed_count


def _normalize_pixel_coordinates(
    pixel_coordinates: Sequence[PixelCoordinate],
) -> List[PixelCoordinate]:
    normalized: List[PixelCoordinate] = []

    for coordinate in pixel_coordinates:
        if len(coordinate) != 2:
            raise AutomationError(f"Invalid pixel coordinate: {coordinate!r}")

        raw_x, raw_y = coordinate
        try:
            x = int(raw_x)
            y = int(raw_y)
        except (TypeError, ValueError) as exc:
            raise AutomationError(f"Pixel coordinate must contain integers: {coordinate!r}") from exc

        normalized.append((x, y))

    return normalized
