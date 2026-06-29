import json
import logging
import uuid
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class ParentStore:
    """File-backed store for parent chunk texts keyed by UUID."""

    def __init__(self, store_path: Path) -> None:
        self._path = store_path / "parents.json"
        self._data: dict = {}
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text())
            except Exception:
                LOGGER.warning("Could not load parent store; starting fresh.")

    def save(self, parent_id: str, text: str) -> None:
        self._data[parent_id] = text
        self._path.write_text(json.dumps(self._data))

    def save_all(self, parent_texts: dict) -> None:
        """Bulk write — one disk write for all parents (use instead of repeated save())."""
        self._data.update(parent_texts)
        self._path.write_text(json.dumps(self._data))

    def get(self, parent_id: str) -> str:
        return self._data.get(parent_id, "")

    def clear(self) -> None:
        self._data = {}
        if self._path.exists():
            self._path.unlink()

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
