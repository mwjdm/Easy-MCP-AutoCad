"""Compatibility facade for code that previously used the COM manager."""

from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from dxf_backend import DXFBackend


class AutoCADManager:
    """Manage an AutoCAD-compatible DXF document without Windows COM."""

    def __init__(self, drawing_path: Optional[str | Path] = None):
        self.backend = DXFBackend(drawing_path=drawing_path)

    def connect(self) -> bool:
        if not self.backend.drawing_path.exists():
            self.backend.new_drawing()
        return True

    def disconnect(self) -> None:
        return None

    @contextmanager
    def autocad_session(self):
        self.connect()
        try:
            yield self
        finally:
            self.disconnect()

    def create_new_drawing(self, template: Optional[str] = None) -> str:
        path = self.backend.new_drawing(template=template)
        return f"Created DXF drawing: {path}"

    def create_layer(self, layer_name: str, color: int = 7) -> str:
        self.backend.create_layer(layer_name, color)
        return f"Layer '{layer_name}' set to color {color}."

    def draw_line(
        self, start_x: float, start_y: float, end_x: float, end_y: float, layer: Optional[str] = None
    ) -> str:
        handle = self.backend.draw_line(start_x, start_y, end_x, end_y, layer)
        return f"Created line, handle: {handle}."

    def export_drawing(self, file_path: str, file_type: str = "DXF") -> str:
        if file_type.upper() != "DXF":
            return "The macOS backend writes DXF only; open it in AutoCAD to export DWG or PDF."
        source = self.backend.drawing_path
        target = Path(file_path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        return f"Exported drawing to {target}."

    def get_entity_stats(self) -> dict[str, int]:
        _, counts = self.backend.scan_all_entities()
        return counts
