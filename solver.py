"""High-performance Word Hunt board solver.

The solver builds a 4x4 grid from sixteen row-major letters, pre-indexes a
dictionary into complete words and prefixes, then performs prefix-pruned DFS
from every tile while preventing tile reuse within a path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple


Coordinate = Tuple[int, int]
CoordinatePath = List[Coordinate]
SolvedWord = Tuple[str, CoordinatePath]

BOARD_SIZE = 4
BOARD_TILE_COUNT = BOARD_SIZE * BOARD_SIZE
DEFAULT_MIN_WORD_LENGTH = 3
MAX_WORD_LENGTH = BOARD_TILE_COUNT


class WordHuntSolverError(Exception):
    """Base exception for Word Hunt solver failures."""


class InvalidBoardError(WordHuntSolverError):
    """Raised when the supplied board letters cannot form a 4x4 board."""


class DictionaryLoadError(WordHuntSolverError):
    """Raised when the local dictionary cannot be loaded safely."""


class WordHuntSolver:
    """Solve a Word Hunt board using prefix-pruned graph traversal.

    Args:
        letters: Sixteen alphabetic characters in row-major order.
        dictionary_path: Path to a local newline-delimited English dictionary.
        min_word_length: Minimum emitted word length. Word Hunt normally scores
            words of length three and above.
    """

    _NEIGHBOR_OFFSETS: Sequence[Coordinate] = (
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    )

    def __init__(
        self,
        letters: str,
        dictionary_path: str,
        min_word_length: int = DEFAULT_MIN_WORD_LENGTH,
    ) -> None:
        self.min_word_length = self._validate_min_word_length(min_word_length)
        self.letters = self._normalize_letters(letters)
        self.grid = self._build_grid(self.letters)
        self.valid_words, self.valid_prefixes = self._load_dictionary(
            dictionary_path=dictionary_path,
            min_word_length=self.min_word_length,
        )

    def solve(self) -> List[SolvedWord]:
        """Return unique valid words with their coordinate paths.

        Results are sorted by longest word first to prioritize high-value
        submissions during automation. Ties are sorted alphabetically for
        deterministic output.
        """

        found_words: Dict[str, CoordinatePath] = {}

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                self._dfs(
                    row=row,
                    col=col,
                    current=self.grid[row][col],
                    path=[(row, col)],
                    visited={(row, col)},
                    found_words=found_words,
                )

        return [
            (word, path)
            for word, path in sorted(
                found_words.items(),
                key=lambda item: (-len(item[0]), item[0]),
            )
        ]

    def _dfs(
        self,
        row: int,
        col: int,
        current: str,
        path: CoordinatePath,
        visited: Set[Coordinate],
        found_words: Dict[str, CoordinatePath],
    ) -> None:
        """Recursive DFS with explicit visited-state propagation."""

        if current not in self.valid_prefixes:
            return

        if len(current) >= self.min_word_length and current in self.valid_words:
            found_words.setdefault(current, list(path))

        if len(current) >= MAX_WORD_LENGTH:
            return

        for row_delta, col_delta in self._NEIGHBOR_OFFSETS:
            next_row = row + row_delta
            next_col = col + col_delta
            next_coord = (next_row, next_col)

            if not self._is_on_board(next_row, next_col):
                continue
            if next_coord in visited:
                continue

            self._dfs(
                row=next_row,
                col=next_col,
                current=current + self.grid[next_row][next_col],
                path=path + [next_coord],
                visited=visited | {next_coord},
                found_words=found_words,
            )

    @staticmethod
    def _validate_min_word_length(min_word_length: int) -> int:
        if min_word_length < 1:
            raise ValueError("min_word_length must be at least 1.")
        if min_word_length > MAX_WORD_LENGTH:
            raise ValueError(
                f"min_word_length must not exceed {MAX_WORD_LENGTH} for a 4x4 board."
            )
        return min_word_length

    @staticmethod
    def _normalize_letters(letters: str) -> str:
        normalized = "".join(letters.lower().split())
        if len(normalized) != BOARD_TILE_COUNT:
            raise InvalidBoardError(
                f"Expected exactly {BOARD_TILE_COUNT} letters, got {len(normalized)}."
            )
        if not normalized.isalpha():
            raise InvalidBoardError("Board letters must contain alphabetic characters only.")
        return normalized

    @staticmethod
    def _build_grid(letters: str) -> List[List[str]]:
        return [
            list(letters[row_start : row_start + BOARD_SIZE])
            for row_start in range(0, BOARD_TILE_COUNT, BOARD_SIZE)
        ]

    @staticmethod
    def _load_dictionary(
        dictionary_path: str,
        min_word_length: int,
    ) -> Tuple[Set[str], Set[str]]:
        path = Path(dictionary_path).expanduser()

        if not path.exists():
            raise DictionaryLoadError(f"Dictionary file does not exist: {path}")
        if not path.is_file():
            raise DictionaryLoadError(f"Dictionary path is not a file: {path}")

        valid_words: Set[str] = set()
        valid_prefixes: Set[str] = set()

        try:
            with path.open("r", encoding="utf-8") as dictionary_file:
                for line_number, raw_line in enumerate(dictionary_file, start=1):
                    word = raw_line.strip().lower()

                    if not word:
                        continue
                    if not word.isalpha():
                        continue
                    if len(word) > MAX_WORD_LENGTH:
                        continue

                    if len(word) >= min_word_length:
                        valid_words.add(word)

                    for prefix_length in range(1, len(word) + 1):
                        valid_prefixes.add(word[:prefix_length])
        except PermissionError as exc:
            raise DictionaryLoadError(f"Permission denied reading dictionary: {path}") from exc
        except UnicodeDecodeError as exc:
            raise DictionaryLoadError(
                f"Dictionary must be UTF-8 text; failed decoding {path}: {exc}"
            ) from exc
        except OSError as exc:
            raise DictionaryLoadError(f"Could not read dictionary {path}: {exc}") from exc

        if not valid_words:
            raise DictionaryLoadError(
                f"No usable words of length {min_word_length}-{MAX_WORD_LENGTH} "
                f"were found in dictionary: {path}"
            )

        return valid_words, valid_prefixes

    @staticmethod
    def _is_on_board(row: int, col: int) -> bool:
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE
