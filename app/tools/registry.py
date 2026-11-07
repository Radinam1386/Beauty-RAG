from app.auth.identity import Identity
from app.listings.service import ListingService
from app.tools.base import Tool, ToolRegistry, ToolResult
from app.tools.listing import build_listing_tools
from app.tools.knowledge import build_knowledge_tools


def default_registry(
    *,
    include_listing_tools: bool = False,
    include_knowledge_tools: bool = True,
    identity: Identity | None = None,
    listing_service: ListingService | None = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    if include_listing_tools:
        for tool in build_listing_tools(identity, service=listing_service):
            registry.register(tool)
    if include_knowledge_tools:
        for tool in build_knowledge_tools():
            registry.register(tool)
    return registry
