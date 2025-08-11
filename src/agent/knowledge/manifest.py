from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


MANIFEST_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sources_manifest.json")


@dataclass(frozen=True)
class SourceEntry:
    id: str
    title: str
    type: str
    path: str
    citation: str
    scope: List[str]


class SourcesManifest:
    def __init__(self, sources: List[SourceEntry]):
        self.sources = sources

    @classmethod
    def load(cls, path: Optional[str] = None) -> "SourcesManifest":
        manifest_path = path or MANIFEST_PATH
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries: List[SourceEntry] = []
        for item in data.get("sources", []):
            entries.append(
                SourceEntry(
                    id=item["id"],
                    title=item["title"],
                    type=item["type"],
                    path=item["path"],
                    citation=item.get("citation", ""),
                    scope=item.get("scope", []),
                )
            )
        return cls(entries)

    def by_type(self, source_type: str) -> List[SourceEntry]:
        return [s for s in self.sources if s.type == source_type]

    def find(self, source_id: str) -> Optional[SourceEntry]:
        for s in self.sources:
            if s.id == source_id:
                return s
        return None

    def all(self) -> List[SourceEntry]:
        return list(self.sources)
