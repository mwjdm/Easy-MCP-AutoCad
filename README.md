# Easy MCP AutoCAD - macOS DXF Edition

这是 `zh19980811/Easy-MCP-AutoCad` 的 macOS 适配版本。原项目使用
`win32com.client` 控制 Windows 上的 AutoCAD ActiveX/COM 对象；Autodesk
文档明确说明 ActiveX Automation 在 Mac OS 上不可用。

This fork replaces the Windows-only COM integration with an `ezdxf` backend.
The MCP server creates and edits a selected `.dxf` drawing on disk. AutoCAD for
Mac can open that drawing, and `open_in_autocad` launches it from the MCP
workflow on macOS.

## Compatibility Boundary

- Works on macOS with Python 3.10 or later.
- Produces standard DXF drawings supported by AutoCAD for Mac.
- Does not attach to or modify the currently active DWG window. That behavior
  in the original project relied on Windows-only COM.
- After an MCP edit, reopen or reload the DXF in AutoCAD if it is already open.

Autodesk references:

- [AutoLISP on Mac and ActiveX limitation](https://help.autodesk.com/cloudhelp/2025/ENU/AutoCAD-MAC-AutoLisp/files/GUID-A0E9D801-8BE9-4BF1-85E8-3807E15F3B71.htm)
- [AutoCAD for Mac developer help](https://help.autodesk.com/view/OARXMAC/2026/ENU/)

## Features

- Create or select a DXF drawing.
- Draw lines, circles, polylines, rectangles, and text.
- Create layers and apply AutoCAD color indexes.
- Move, rotate, and copy entities by DXF handle.
- Scan modelspace into SQLite and query/highlight indexed entities.
- Count and color matching text.
- Open the managed drawing in AutoCAD for Mac.

## Install On Mac

```bash
git clone https://github.com/YOUR_ACCOUNT/Easy-MCP-AutoCad.git
cd Easy-MCP-AutoCad
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run the MCP server:

```bash
python server.py
```

By default the managed files are:

```text
./drawings/active.dxf
./autocad_data.db
```

Set another working drawing or database before starting the server:

```bash
export AUTOCAD_DXF_PATH="$HOME/Documents/AutoCAD-MCP/current.dxf"
export AUTOCAD_DB_PATH="$HOME/Documents/AutoCAD-MCP/current.db"
python server.py
```

## Claude Desktop On Mac

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "easy-autocad-mac": {
      "command": "/absolute/path/Easy-MCP-AutoCad/.venv/bin/python",
      "args": ["/absolute/path/Easy-MCP-AutoCad/server.py"],
      "env": {
        "AUTOCAD_DXF_PATH": "/Users/your-name/Documents/AutoCAD-MCP/current.dxf"
      }
    }
  }
}
```

## Typical Workflow

1. Call `create_new_drawing`, optionally supplying `output_path`.
2. Use `create_layer`, `draw_line`, `draw_circle`, `draw_text`, or the other
   drawing tools.
3. Call `open_in_autocad` to open the DXF in AutoCAD for Mac. If the
   installed application name includes a version, pass it as `app_name`, for
   example `AutoCAD 2026`.
4. Call `scan_all_entities` before database queries such as
   `query_and_highlight`.

## Test

The automated tests validate DXF creation, parsing, modelspace geometry,
handles, transforms, color changes, text matching, and the SQLite index. They
do not require an AutoCAD installation.

```bash
python -m pip install -e '.[test]'
pytest -q
```

## Licensing Note

The upstream repository did not include a license file when this macOS
adaptation was prepared on May 26, 2026. This fork retains upstream attribution
and is published through GitHub's fork mechanism; obtain permission from the
upstream author before redistributing the source outside the permissions GitHub
provides for public repositories and forks.
