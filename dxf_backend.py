"""Cross-platform AutoCAD-compatible DXF backend.

AutoCAD for Mac does not expose the Windows ActiveX/COM API.  This module
therefore edits a DXF document on disk using ezdxf.  AutoCAD for Mac can open
the resulting document, while the MCP server remains runnable on macOS.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
from typing import Any, Iterable, Optional

import ezdxf


class DrawingError(RuntimeError):
    """Raised when an operation cannot be performed on the managed drawing."""


class DXFBackend:
    def __init__(
        self,
        drawing_path: Optional[str | Path] = None,
        database_path: Optional[str | Path] = None,
    ) -> None:
        default_drawing = Path.cwd() / "drawings" / "active.dxf"
        self.drawing_path = Path(
            drawing_path or os.environ.get("AUTOCAD_DXF_PATH", default_drawing)
        ).expanduser()
        self.database_path = Path(
            database_path or os.environ.get("AUTOCAD_DB_PATH", Path.cwd() / "autocad_data.db")
        ).expanduser()
        self._init_db()

    def _init_db(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cad_elements (
                    id INTEGER PRIMARY KEY,
                    handle TEXT UNIQUE,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    layer TEXT,
                    properties TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS text_patterns (
                    id INTEGER PRIMARY KEY,
                    pattern TEXT UNIQUE,
                    count INTEGER DEFAULT 0,
                    drawing TEXT
                )
                """
            )

    def new_drawing(
        self, template: Optional[str] = None, output_path: Optional[str] = None
    ) -> Path:
        if output_path:
            self.drawing_path = Path(output_path).expanduser()
        self.drawing_path.parent.mkdir(parents=True, exist_ok=True)
        if template:
            source = Path(template).expanduser()
            if not source.exists():
                raise DrawingError(f"Template not found: {source}")
            doc = ezdxf.readfile(source)
        else:
            doc = ezdxf.new("R2018", setup=True)
        doc.saveas(self.drawing_path)
        return self.drawing_path

    def open_drawing(self, path: str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.exists():
            raise DrawingError(f"Drawing not found: {candidate}")
        ezdxf.readfile(candidate)
        self.drawing_path = candidate
        return candidate

    def _read(self):
        if not self.drawing_path.exists():
            raise DrawingError("No drawing selected. Use create_new_drawing or open_drawing first.")
        return ezdxf.readfile(self.drawing_path)

    def _save(self, doc) -> None:
        doc.saveas(self.drawing_path)

    @staticmethod
    def _layer(doc, layer: Optional[str]) -> str:
        name = layer or "0"
        if not doc.layers.has_entry(name):
            doc.layers.new(name)
        return name

    @staticmethod
    def _validate_color(color: int) -> int:
        if not 1 <= color <= 255:
            raise DrawingError("Color index must be from 1 to 255.")
        return color

    @staticmethod
    def _handle(entity) -> str:
        return str(entity.dxf.handle)

    def create_layer(self, name: str, color_index: int = 7) -> str:
        color = self._validate_color(color_index)
        doc = self._read()
        if doc.layers.has_entry(name):
            doc.layers.get(name).dxf.color = color
        else:
            doc.layers.new(name, dxfattribs={"color": color})
        self._save(doc)
        return name

    def draw_line(
        self, start_x: float, start_y: float, end_x: float, end_y: float, layer: Optional[str] = None
    ) -> str:
        doc = self._read()
        layer_name = self._layer(doc, layer)
        entity = doc.modelspace().add_line(
            (start_x, start_y, 0), (end_x, end_y, 0), dxfattribs={"layer": layer_name}
        )
        self._save(doc)
        return self._handle(entity)

    def draw_circle(
        self, center_x: float, center_y: float, radius: float, layer: Optional[str] = None
    ) -> str:
        if radius <= 0:
            raise DrawingError("Radius must be greater than zero.")
        doc = self._read()
        layer_name = self._layer(doc, layer)
        entity = doc.modelspace().add_circle(
            (center_x, center_y, 0), radius, dxfattribs={"layer": layer_name}
        )
        self._save(doc)
        return self._handle(entity)

    def draw_polyline(
        self, points: list[float], closed: bool = False, layer: Optional[str] = None
    ) -> str:
        if len(points) < 4 or len(points) % 2:
            raise DrawingError("Polyline points must be [x1, y1, x2, y2, ...].")
        vertices = list(zip(points[0::2], points[1::2]))
        doc = self._read()
        layer_name = self._layer(doc, layer)
        entity = doc.modelspace().add_lwpolyline(
            vertices, close=closed, dxfattribs={"layer": layer_name}
        )
        self._save(doc)
        return self._handle(entity)

    def draw_text(
        self,
        text_string: str,
        insert_x: float,
        insert_y: float,
        height: float = 2.5,
        rotation: float = 0,
        layer: Optional[str] = None,
    ) -> str:
        if height <= 0:
            raise DrawingError("Text height must be greater than zero.")
        doc = self._read()
        layer_name = self._layer(doc, layer)
        entity = doc.modelspace().add_text(
            text_string,
            dxfattribs={"height": height, "rotation": rotation, "layer": layer_name},
        )
        entity.dxf.insert = (insert_x, insert_y, 0)
        self._save(doc)
        return self._handle(entity)

    def _entity(self, doc, handle: str):
        entity = doc.entitydb.get(handle.upper())
        if entity is None or not entity.is_alive:
            raise DrawingError(f"Entity handle not found: {handle}")
        return entity

    @staticmethod
    def _properties(entity) -> dict[str, Any]:
        entity_type = entity.dxftype()
        if entity_type == "LINE":
            return {"start_point": list(entity.dxf.start), "end_point": list(entity.dxf.end)}
        if entity_type == "CIRCLE":
            return {"center": list(entity.dxf.center), "radius": entity.dxf.radius}
        if entity_type in {"TEXT", "MTEXT"}:
            text = entity.dxf.text if entity_type == "TEXT" else entity.text
            return {"text": text, "position": list(entity.dxf.insert)}
        if entity_type == "LWPOLYLINE":
            return {"points": [list(point[:2]) for point in entity.get_points()], "closed": entity.closed}
        return {}

    def scan_all_entities(self) -> tuple[int, dict[str, int]]:
        doc = self._read()
        counts: dict[str, int] = {}
        with sqlite3.connect(self.database_path) as conn:
            conn.execute("DELETE FROM cad_elements")
            for entity in doc.modelspace():
                entity_type = entity.dxftype()
                counts[entity_type] = counts.get(entity_type, 0) + 1
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cad_elements
                        (handle, name, type, layer, properties)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        self._handle(entity),
                        entity_type.title(),
                        entity_type,
                        entity.dxf.get("layer", "0"),
                        json.dumps(self._properties(entity)),
                    ),
                )
        return sum(counts.values()), counts

    def set_color(self, handles: Iterable[str], color: int) -> int:
        self._validate_color(color)
        doc = self._read()
        changed = 0
        for handle in handles:
            try:
                self._entity(doc, handle).dxf.color = color
                changed += 1
            except DrawingError:
                continue
        self._save(doc)
        return changed

    def count_text_patterns(self, pattern: str) -> tuple[int, list[dict[str, Any]]]:
        doc = self._read()
        matches = []
        for entity in doc.modelspace():
            if entity.dxftype() not in {"TEXT", "MTEXT"}:
                continue
            text = entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
            if pattern in text:
                matches.append(
                    {
                        "handle": self._handle(entity),
                        "text": text,
                        "layer": entity.dxf.get("layer", "0"),
                    }
                )
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO text_patterns (pattern, count, drawing) VALUES (?, ?, ?)",
                (pattern, len(matches), self.drawing_path.name),
            )
        return len(matches), matches

    def highlight_text_matches(self, pattern: str, color: int) -> int:
        _, matches = self.count_text_patterns(pattern)
        return self.set_color((match["handle"] for match in matches), color)

    def translate(self, handle: str, start_point: list[float], end_point: list[float]) -> None:
        if len(start_point) < 2 or len(end_point) < 2:
            raise DrawingError("Points must contain at least x and y.")
        doc = self._read()
        entity = self._entity(doc, handle)
        dz = (end_point[2] if len(end_point) > 2 else 0) - (
            start_point[2] if len(start_point) > 2 else 0
        )
        entity.translate(end_point[0] - start_point[0], end_point[1] - start_point[1], dz)
        self._save(doc)

    def rotate(self, handle: str, base_point: list[float], angle: float) -> None:
        if len(base_point) < 2:
            raise DrawingError("Base point must contain at least x and y.")
        doc = self._read()
        entity = self._entity(doc, handle)
        x, y = base_point[0], base_point[1]
        entity.translate(-x, -y, 0)
        entity.rotate_z(math.radians(angle))
        entity.translate(x, y, 0)
        self._save(doc)

    def copy_entity(self, handle: str, start_point: list[float], end_point: list[float]) -> str:
        doc = self._read()
        source = self._entity(doc, handle)
        entity = source.copy()
        doc.modelspace().add_entity(entity)
        dz = (end_point[2] if len(end_point) > 2 else 0) - (
            start_point[2] if len(start_point) > 2 else 0
        )
        entity.translate(end_point[0] - start_point[0], end_point[1] - start_point[1], dz)
        self._save(doc)
        return self._handle(entity)

    def execute_query(self, query: str) -> str:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(query)
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                return json.dumps([dict(zip(columns, row)) for row in cursor.fetchall()], indent=2)
            return f"Query completed, affected rows: {cursor.rowcount}"

    def query_handles(self, query: str) -> list[str]:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute(query)
            columns = [column[0].lower() for column in (cursor.description or [])]
            if "handle" not in columns:
                raise DrawingError("Query result must contain a handle column.")
            index = columns.index("handle")
            return [str(row[index]) for row in cursor.fetchall()]

    def open_in_autocad(self, app_name: str = "AutoCAD") -> Path:
        if platform.system() != "Darwin":
            raise DrawingError("Opening AutoCAD automatically is available on macOS only.")
        self._read()
        result = subprocess.run(
            ["open", "-a", app_name, str(self.drawing_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            detail = result.stderr.strip() or "AutoCAD application was not found."
            raise DrawingError(detail)
        return self.drawing_path
