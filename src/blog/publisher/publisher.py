from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class Publisher(ABC):
    """Abstract base class for CMS publishing implementations."""

    @abstractmethod
    async def add_draft(self, item: dict) -> str:
        """Create a draft CMS item from a post dict. Returns the provider-assigned item ID."""

    @abstractmethod
    async def list_items(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Return collection items, optionally filtered to those on or after `since`."""

    @abstractmethod
    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """Retrieve a single item by its provider ID."""

    @abstractmethod
    async def publish_draft(self, item_id: str) -> None:
        """Promote a draft item to live."""

    @abstractmethod
    async def delete_item(self, item_id: str) -> None:
        """Remove an item from the collection."""

    async def aclose(self) -> None:
        """Release any underlying HTTP client resources. Override if needed."""
