from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Issue(BaseModel):
    document: str
    section: Optional[str] = None
    issue: str
    severity: str = Field(default="Info")
    suggestion: Optional[str] = None


class FileReport(BaseModel):
    filename: str
    document_type: Optional[str] = None
    structure_summary: Dict[str, Any]
    issues_found: List[Issue] = Field(default_factory=list)


class BatchReport(BaseModel):
    process: str = Field(default="Unknown (Phase 1)")
    documents_uploaded: int
    required_documents: int = 0
    missing_documents: List[str] = Field(default_factory=list)
    files: List[FileReport]

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)
