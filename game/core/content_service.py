from __future__ import annotations

"""Compatibility shim for legacy imports.

Use `game.services.content_service.ContentService` as source of truth.
"""

from game.services.content_service import ContentService as _ServiceContentService


class ContentService(_ServiceContentService):
    pass
