# Usage Guide

## Table of Contents

1. [GUI Mode](#gui-mode) (Recommended for beginners)
2. [Command Line](#command-line) (For scripting)
3. [Batch Processing](#batch-processing)
4. [Advanced Options](#advanced-options)
5. [Examples](#examples)

---

## GUI Mode

Launch the graphical interface for interactive notebook conversion:

```bash
python nbk_convert.py --gui
```

### Features

- 📁 **Browse & Select** - Choose notebook directories
- 🔍 **Preview** - See PDF names before conversion
- ☑️ **Selective Conversion** - Convert only selected notebooks
- 📱 **Kindle Sync** - Connect and sync via MTP (Windows)
- ⚙️ **Options** - Configure behavior with checkboxes

### Workflow

1. **Connect Kindle** (optional)
   - Click "Connect Kindle" button
   - Program detects Kindle Scribe via USB/MTP
   - Notebooks are cached to local folder

2. **Scan Notebooks**
   - Click "Scan Notebooks"
   - Program discovers all `.nbk` files
   - Shows folder names and PDF preview names

3. **Configure Options**
   - ✓ "Skip Existing PDFs" - Don't overwrite
   - ✓ "Use Clean Title" - Extract title from metadata
   - ✓ "Only Selected" - Convert checked notebooks only

4. **Convert**
   - Click "Convert" button
   - Progress bar shows completion
   - Activity log displays results

---

## Command Line

### Basic Usage

#### Single Notebook

```bash
python nbk_convert.py /path/to/notebook output.pdf
```

#### Notebook Directory

```bash
python nbk_convert.py /path/to/notebook/
```

PDF is created next to the notebook directory with the directory name.

### Options

```
positional arguments:
  input                 NBK file, notebook directory, or batch root
  output               Output file (.pdf) or batch directory

optional arguments:
  --batch              Batch convert all notebooks recursively
  --skip-existing      Skip if output PDF already exists
  --use-title          Use title from notebook metadata
  --dry-run            Preview without writing
  --plugin-dir PATH    Path to kfxlib directory
  --gui                Launch graphical interface
  -h, --help           Show this help message
```

---

## Batch Processing

### Convert All Notebooks

```bash
python nbk_convert.py /notebooks --batch
```

Finds all `.nbk` files recursively and converts them.

### With Output Directory

```bash
python nbk_convert.py /notebooks --batch --output /output/path
```

PDFs are saved to `/output/path` with same directory structure.

### Skip Existing

```bash
python nbk_convert.py /notebooks --batch --skip-existing
```

Useful for resuming interrupted batch jobs.

### Use Titles

```bash
python nbk_convert.py /notebooks --batch --use-title
```

Derives PDF names from notebook metadata instead of UUIDs.

### Dry Run

```bash
python nbk_convert.py /notebooks --batch --dry-run
```

Preview operations without actually converting.

### Combined

```bash
python nbk_convert.py /notebooks \
  --batch \
  --output /output \
  --skip-existing \
  --use-title \
  --plugin-dir /custom/kfx_plugin
```

---

## Advanced Options

### Custom KFX Plugin

```bash
python nbk_convert.py input --plugin-dir /path/to/kfx_plugin
```

Or set environment variable:

```bash
export KFX_PLUGIN_DIR="/path/to/kfx_plugin"
python nbk_convert.py input
```

### MTP Device Name

If using a custom device name (not "Kindle Scribe"):

```python
from kindle_notebook_pdf_converter.nbk_convert import sync_kindle_notebooks_via_mtp

local_root, count = sync_kindle_notebooks_via_mtp(
    device_name="My Device",
    target_root="D:\\cache"
)
```

### Programmatic API

```python
from kindle_notebook_pdf_converter.nbk_convert import convert, extract_pages

# Convert single notebook
stats = convert(
    input_path="/path/to/nbk",
    output_path="output.pdf",
    plugin_dir="/path/to/kfx_plugin"
)

print(f"Pages: {stats['n_pages']}")
print(f"Strokes: {stats['n_strokes']}")
print(f"Per page: {stats['page_strokes']}")
```

---

## Examples

### Example 1: Simple Single Conversion

```bash
python nbk_convert.py "D:\Kindle\notebook1\nbk" "notebook1.pdf"
```

Result: `notebook1.pdf` in current directory

### Example 2: Batch Convert with Titles

```bash
cd D:\kindle_notebook_pdf_converter
python nbk_convert.py D:\Kindle --batch --output D:\PDFs --use-title
```

Result: PDFs with clean titles in `D:\PDFs`

### Example 3: Resume Interrupted Batch

```bash
python nbk_convert.py D:\Kindle --batch --output D:\PDFs --skip-existing
```

Continues where previous run stopped.

### Example 4: Preview Before Converting

```bash
python nbk_convert.py D:\Kindle --batch --dry-run
```

Shows what would be converted without writing files.

### Example 5: Custom Plugin Directory

```bash
python nbk_convert.py \
  D:\Kindle \
  --batch \
  --plugin-dir "C:\Libraries\calibre-plugins\kfx_plugin"
```

### Example 6: Python Script

```python
#!/usr/bin/env python3
from kindle_notebook_pdf_converter.nbk_convert import convert

# Single conversion
stats = convert(
    input_path="notebooks/notebook1/nbk",
    output_path="notebook1.pdf",
    plugin_dir="kfx_plugin"
)

print(f"Converted: {stats['n_pages']} pages, {stats['n_strokes']} strokes")
```

### Example 7: Batch with Error Handling

```python
from kindle_notebook_pdf_converter.nbk_convert import convert, find_all_nbk_dirs

root_dir = "D:\\Kindle"
notebooks = find_all_nbk_dirs(root_dir)

for nbk_file, default_pdf, dir_name in notebooks:
    try:
        stats = convert(nbk_file, default_pdf, "kfx_plugin")
        print(f"✓ {dir_name}")
    except Exception as e:
        print(f"✗ {dir_name}: {e}")
```

---

## Output Details

### PDF Quality

Generated PDFs contain:
- ✅ Vector strokes (scalable, lossless)
- ✅ Exact colors preserved
- ✅ Pen thickness information
- ✅ Highlighter transparency (20%)
- ✅ Background guide lines

### File Size

- Typical notebook: 2-10 MB
- Complex notebook: 10-50 MB
- Depends on stroke count and image content

### Coordinate System

- Canvas: 2520 PPI (sub-pixel precision)
- Page size: ~5.8" × 8.0" (Scribe screen dimensions)
- Color: 24-bit RGB (millions of colors)

---

## Troubleshooting

### "NBK file not found"

```bash
# Verify file exists
ls -la /path/to/notebook/nbk

# Or search for all notebooks
python nbk_convert.py /path/to/notebooks --batch --dry-run
```

### "Invalid signature" Error

NBK file is corrupted. Options:
1. Copy notebook again from Kindle
2. Use backup if available
3. Check file with `file` command

### GUI Won't Start

```bash
# Test Tk installation
python -m tkinter

# If fails, install tkinter
sudo apt-get install python3-tk  # Linux
brew install python-tk@3.11       # macOS
```

### Slow Performance

- Use `--batch` mode for multiple notebooks
- Disable transparent backgrounds if not needed
- Increase available RAM
- Use solid-state drive for output

### MTP Issues (Windows)

```bash
# Check device name
Get-PnpDevice -InstanceId "USB\VID_*"

# Update driver through Windows Device Manager
```

---

## Tips & Tricks

### Create Desktop Shortcut (Windows)

```powershell
$shortcut = New-Object -ComObject WScript.Shell
$link = $shortcut.CreateShortcut("$env:UserProfile\Desktop\NBK Converter.lnk")
$link.TargetPath = "python.exe"
$link.Arguments = "$PSScriptRoot\nbk_convert.py --gui"
$link.WorkingDirectory = $PSScriptRoot
$link.Save()
```

### Automate Conversions (via Cron/Task Scheduler)

```bash
# Linux/macOS: Add to crontab
0 2 * * * /home/user/downloader/.venv/bin/python /home/user/downloader/kindle_notebook_pdf_converter/nbk_convert.py /notebooks --batch --skip-existing

# Windows: Use Task Scheduler (PowerShell)
$action = New-ScheduledTaskAction -Execute "python" -Argument "nbk_convert.py --batch --skip-existing /notebooks"
Register-ScheduledTask -TaskName "Convert Notebooks" -Action $action -Trigger (New-ScheduledTaskTrigger -Daily -At 2am)
```

### Monitor Conversions

```python
# Track progress with logging
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    filename='conversions.log'
)
```

---

See also: [Installation](installation.md), [Architecture](architecture.md), [README](../README.md)
