from typing import Optional

from src.models import ContentAnalysis, ContentItem


def get_analysis(item: ContentItem) -> Optional[ContentAnalysis]:
    """Return the item's AI analysis, if any."""
    return item.processing.analysis if item.processing else None
