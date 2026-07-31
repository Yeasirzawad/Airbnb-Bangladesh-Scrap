from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "pipeline.yaml"


class Config:
    """Loads pipeline.yaml and resolves every `paths.*` entry to an absolute Path."""

    def __init__(self, data: dict[str, Any], root: Path):
        self._data = data
        self.root = root

    @classmethod
    def load(cls, path: Path | str = DEFAULT_CONFIG_PATH) -> "Config":
        path = Path(path)
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(data, root=PROJECT_ROOT)

    def path(self, dotted_key: str) -> Path:
        """Resolve e.g. 'raw.district_links' or 'processed.reviews' to an absolute Path."""
        section, key = dotted_key.split(".", 1)
        rel = self._data["paths"][section][key]
        return self.root / rel

    def get(self, dotted_key: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def valid_bd_divisions(self) -> list[str]:
        return self.get("divisions.valid_bd_divisions", [])

    @property
    def host_verification_badges(self) -> list[str]:
        return self.get("host_verification_badges", [])
