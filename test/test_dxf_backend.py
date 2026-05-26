import json
import sqlite3

import ezdxf

from dxf_backend import DXFBackend


def make_backend(tmp_path):
    backend = DXFBackend(tmp_path / "drawing.dxf", tmp_path / "drawing.db")
    backend.new_drawing()
    return backend


def test_creates_autocad_compatible_geometry_and_index(tmp_path):
    backend = make_backend(tmp_path)
    backend.create_layer("MCP", 1)
    line = backend.draw_line(0, 0, 20, 0, "MCP")
    circle = backend.draw_circle(5, 5, 3, "MCP")
    backend.draw_polyline([0, 0, 10, 0, 10, 10, 0, 10], closed=True, layer="MCP")
    backend.draw_text("PMC-3M / Mac", 2, 2, layer="MCP")

    count, types = backend.scan_all_entities()
    assert count == 4
    assert types == {"LINE": 1, "CIRCLE": 1, "LWPOLYLINE": 1, "TEXT": 1}

    matches, entries = backend.count_text_patterns("PMC-3M")
    assert matches == 1
    assert entries[0]["text"] == "PMC-3M / Mac"

    backend.set_color([line, circle], 3)
    doc = ezdxf.readfile(backend.drawing_path)
    assert doc.entitydb[line].dxf.color == 3
    assert doc.entitydb[circle].dxf.color == 3

    with sqlite3.connect(backend.database_path) as connection:
        stored = connection.execute("SELECT COUNT(*) FROM cad_elements").fetchone()[0]
    assert stored == 4


def test_transforms_copy_and_database_query_highlight(tmp_path):
    backend = make_backend(tmp_path)
    handle = backend.draw_line(0, 0, 10, 0)
    backend.translate(handle, [0, 0, 0], [2, 4, 0])
    backend.rotate(handle, [2, 4, 0], 90)
    copied = backend.copy_entity(handle, [0, 0, 0], [10, 0, 0])
    backend.scan_all_entities()

    handles = backend.query_handles("SELECT handle FROM cad_elements")
    assert handles == [handle, copied]
    assert backend.set_color(handles, 2) == 2

    doc = ezdxf.readfile(backend.drawing_path)
    assert len(list(doc.modelspace())) == 2
    assert doc.entitydb[copied].dxf.color == 2
    results = json.loads(backend.execute_query("SELECT type FROM cad_elements ORDER BY handle"))
    assert results == [{"type": "LINE"}, {"type": "LINE"}]
