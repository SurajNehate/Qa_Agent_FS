"""Load and validate evaluation datasets."""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """A single evaluation test case."""

    question: str
    expected_keywords: list[str] = Field(default_factory=list)
    category: str = "general"


def load_dataset(path: str) -> list[EvalCase]:
    """Load evaluation dataset from a JSON file.

    Args:
        path: Path to a JSON file containing a list of eval cases.

    Returns:
        List of validated EvalCase objects.

    Raises:
        FileNotFoundError: If the dataset file doesn't exist.
        ValueError: If the JSON is not a list or contains invalid entries.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON array, got {type(raw).__name__}")

    cases = []
    for i, item in enumerate(raw):
        try:
            cases.append(EvalCase(**item))
        except Exception as e:
            raise ValueError(f"Invalid eval case at index {i}: {e}") from e

    return cases
