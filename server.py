"""MCP tools for managing an AutoCAD-compatible DXF drawing on macOS."""

from __future__ import annotations

import json
from typing import List, Optional

from mcp.server.fastmcp import Context, FastMCP

from dxf_backend import DXFBackend


mcp = FastMCP("AutoCAD-DXF-Mac-Server")
backend = DXFBackend()


def _failure(action: str, error: Exception) -> str:
    return f"{action} failed: {error}"


@mcp.tool()
def create_new_drawing(
    ctx: Context, template: Optional[str] = None, output_path: Optional[str] = None
) -> str:
    """Create and select a new DXF drawing that AutoCAD for Mac can open."""
    try:
        return f"Created DXF drawing: {backend.new_drawing(template, output_path)}"
    except Exception as error:
        return _failure("Create drawing", error)


@mcp.tool()
def open_drawing(ctx: Context, path: str) -> str:
    """Select an existing DXF drawing for subsequent tool calls."""
    try:
        return f"Selected DXF drawing: {backend.open_drawing(path)}"
    except Exception as error:
        return _failure("Open drawing", error)


@mcp.tool()
def open_in_autocad(ctx: Context, app_name: str = "AutoCAD") -> str:
    """Open the selected DXF in AutoCAD for Mac using the macOS application name."""
    try:
        return f"Opened drawing in {app_name}: {backend.open_in_autocad(app_name)}"
    except Exception as error:
        return _failure("Open in AutoCAD", error)


@mcp.tool()
def create_layer(ctx: Context, name: str, color_index: int = 7) -> str:
    """Create or update a drawing layer."""
    try:
        backend.create_layer(name, color_index)
        return f"Layer '{name}' set to color {color_index}."
    except Exception as error:
        return _failure("Set layer", error)


@mcp.tool()
def draw_line(
    ctx: Context,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    layer: Optional[str] = None,
) -> str:
    """Draw a line in the selected DXF document."""
    try:
        handle = backend.draw_line(start_x, start_y, end_x, end_y, layer)
        return f"Created line, handle: {handle}."
    except Exception as error:
        return _failure("Draw line", error)


@mcp.tool()
def draw_circle(
    ctx: Context,
    center_x: float,
    center_y: float,
    radius: float,
    layer: Optional[str] = None,
) -> str:
    """Draw a circle in the selected DXF document."""
    try:
        handle = backend.draw_circle(center_x, center_y, radius, layer)
        return f"Created circle, handle: {handle}."
    except Exception as error:
        return _failure("Draw circle", error)


@mcp.tool()
def draw_polyline(
    ctx: Context, points: List[float], closed: bool = False, layer: Optional[str] = None
) -> str:
    """Draw a lightweight polyline from a flat x/y point list."""
    try:
        handle = backend.draw_polyline(points, closed, layer)
        return f"Created polyline, handle: {handle}."
    except Exception as error:
        return _failure("Draw polyline", error)


@mcp.tool()
def draw_rectangle(
    ctx: Context, x1: float, y1: float, x2: float, y2: float, layer: Optional[str] = None
) -> str:
    """Draw a closed rectangular polyline."""
    try:
        handle = backend.draw_polyline([x1, y1, x2, y1, x2, y2, x1, y2], True, layer)
        return f"Created rectangle, handle: {handle}."
    except Exception as error:
        return _failure("Draw rectangle", error)


@mcp.tool()
def draw_text(
    ctx: Context,
    text_string: str,
    insert_x: float,
    insert_y: float,
    height: float = 2.5,
    rotation: float = 0,
    layer: Optional[str] = None,
) -> str:
    """Draw one-line text."""
    try:
        handle = backend.draw_text(text_string, insert_x, insert_y, height, rotation, layer)
        return f"Created text '{text_string}', handle: {handle}."
    except Exception as error:
        return _failure("Draw text", error)


@mcp.tool()
def scan_all_entities(ctx: Context) -> str:
    """Scan the DXF modelspace into the SQLite entity index."""
    try:
        count, entity_types = backend.scan_all_entities()
        return f"Indexed {count} entities: {json.dumps(entity_types, sort_keys=True)}"
    except Exception as error:
        return _failure("Scan drawing", error)


@mcp.tool()
def highlight_entity(ctx: Context, handle: str, color: int = 1) -> str:
    """Apply an AutoCAD color index to an entity by its DXF handle."""
    try:
        changed = backend.set_color([handle], color)
        return (
            f"Set entity {handle} to color {color}."
            if changed
            else f"Entity handle not found: {handle}."
        )
    except Exception as error:
        return _failure("Highlight entity", error)


@mcp.tool()
def count_text_patterns(ctx: Context, pattern: str = "PMC-3M") -> str:
    """Count text elements containing a string."""
    try:
        count, matches = backend.count_text_patterns(pattern)
        return f"Found {count} text matches for '{pattern}': {json.dumps(matches[:10])}"
    except Exception as error:
        return _failure("Count text matches", error)


@mcp.tool()
def highlight_text_matches(ctx: Context, pattern: str = "PMC-3M", color: int = 1) -> str:
    """Apply a color index to all matching text entities."""
    try:
        count = backend.highlight_text_matches(pattern, color)
        return f"Set {count} matching text entities to color {color}."
    except Exception as error:
        return _failure("Highlight text", error)


@mcp.tool()
def move_entity(
    ctx: Context, handle: str, start_point: List[float], end_point: List[float]
) -> str:
    """Move an entity by the displacement between two points."""
    try:
        backend.translate(handle, start_point, end_point)
        return f"Moved entity {handle}."
    except Exception as error:
        return _failure("Move entity", error)


@mcp.tool()
def rotate_entity(ctx: Context, handle: str, base_point: List[float], angle: float) -> str:
    """Rotate an entity about a base point by degrees."""
    try:
        backend.rotate(handle, base_point, angle)
        return f"Rotated entity {handle} by {angle} degrees."
    except Exception as error:
        return _failure("Rotate entity", error)


@mcp.tool()
def copy_entity(
    ctx: Context, handle: str, start_point: List[float], end_point: List[float]
) -> str:
    """Copy and translate an entity."""
    try:
        new_handle = backend.copy_entity(handle, start_point, end_point)
        return f"Copied entity, new handle: {new_handle}."
    except Exception as error:
        return _failure("Copy entity", error)


@mcp.tool()
def get_all_tables(ctx: Context) -> str:
    """List local SQLite index tables."""
    try:
        return backend.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
    except Exception as error:
        return _failure("List database tables", error)


@mcp.tool()
def get_table_schema(ctx: Context, table_name: str) -> str:
    """Read a SQLite table schema."""
    try:
        safe_name = table_name.replace('"', '""')
        return backend.execute_query(f'PRAGMA table_info("{safe_name}")')
    except Exception as error:
        return _failure("Get database schema", error)


@mcp.tool()
def execute_query(ctx: Context, query: str) -> str:
    """Execute a query on the local drawing index database."""
    try:
        return backend.execute_query(query)
    except Exception as error:
        return _failure("Execute query", error)


@mcp.tool()
def query_and_highlight(ctx: Context, sql_query: str, highlight_color: int = 1) -> str:
    """Set colors on entities whose handles are returned by an index query."""
    try:
        handles = backend.query_handles(sql_query)
        count = backend.set_color(handles, highlight_color)
        return f"Set {count} of {len(handles)} queried entities to color {highlight_color}."
    except Exception as error:
        return _failure("Query and highlight", error)


if __name__ == "__main__":
    mcp.run()
