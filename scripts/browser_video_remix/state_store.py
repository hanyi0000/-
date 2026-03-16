import json
from pathlib import Path


class FileStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))
        else:
            self._data = {}

    def update(self, clip_id: str, **values: str) -> None:
        self._data.setdefault(clip_id, {}).update(values)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self, clip_id: str) -> dict[str, str]:
        return self._data[clip_id]
