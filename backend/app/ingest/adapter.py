"""Abstract base for data ingest adapters (OAuth/SFTP/Email/Upload)."""
from abc import ABC, abstractmethod
from typing import Any


class IngestAdapter(ABC):
    """Unified data ingest adapter. All four import modes implement this."""

    @abstractmethod
    def validate_config(self, source: Any) -> bool:
        """Validate data source configuration."""
        ...

    @abstractmethod
    def fetch_settlements(self, source: Any, **kwargs) -> list[dict]:
        """Fetch settlement data. Returns list of raw settlement dicts."""
        ...
