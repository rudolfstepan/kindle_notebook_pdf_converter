# Kindle Scribe Notebook PDF Converter

Converts handwritten notes from Kindle Scribe (`.nbk` files) to PDFs with full vector rendering of strokes.

## Supported input

This tool is intended for Kindle Scribe `.nbk` notebook files exported from a Kindle device.

Other Kindle formats such as `.kfx`, `.azw`, or DRM-protected ebook files are not supported.

## Features

- ✅ Converts Kindle Scribe notebook files (.nbk) to high-quality PDFs
- ✅ **Vector-based stroke rendering** — scalable without quality loss
- ✅ **Color support** — preserves pen colors (ballpoint, marker, highlighter)
- ✅ **Batch conversion** — converts multiple notebooks recursively
- ✅ **Kindle MTP sync** — Windows integration for copying notebooks via MTP
- ✅ **Desktop GUI** — user-friendly interface for selection and conversion
- ✅ **Command-line interface (CLI)** — full control over conversion parameters

## System Requirements

- **Python 3.8+**
- **Windows, macOS, or Linux**
- For MTP sync: **Windows 11** (or later; implemented via PowerShell)

## Installation

### 1. Clone repository

```bash
git clone <repository-url>
cd kindle_notebook_pdf_converter
```

### 2. Create Python Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
& .\.venv\Scripts\Activate.ps1

# macOS/Linux (Bash/Zsh)
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

Recommended: use `setup.py`. It now performs all required setup steps automatically:

- installs the Python runtime dependencies
- downloads the `kfxlib` plugin from the GitHub mirror
- extracts `kfxlib` into `kfx_plugin/`
- registers `kfx_plugin/` so `import kfxlib` works immediately

```bash
# Windows
py setup.py

# macOS/Linux
python3 setup.py
```

This installs these Python packages automatically:

- `reportlab`
- `pypdf`
- `lxml`
- `Pillow`
- `beautifulsoup4`

Alternative manual installation:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Or manually:**

```bash
pip install reportlab>=4.0.0
pip install pypdf>=3.0.0
pip install lxml>=4.9.0
pip install Pillow>=9.0.0
pip install beautifulsoup4>=4.12.0
```

### 4. KFX Plugin (`kfxlib`)

The project requires the `kfxlib` library from John Howell's KFX Input plugin.

`setup.py` now downloads it automatically from the public GitHub mirror:

- `https://github.com/kluyg/calibre-kfx-input`

The downloaded archive is unpacked automatically and only the `kfxlib/` folder is extracted into `kfx_plugin/`.

Manual setup is only needed if the automatic download fails.

#### Manual fallback

1. Clone or download `https://github.com/kluyg/calibre-kfx-input`
2. Extract the ZIP file
3. Navigate to the directory containing `kfxlib/`
4. Copy the `kfxlib` folder to the `kfx_plugin/` directory:
   ```
    kindle_notebook_pdf_converter/
   ├── kfx_plugin/
   │   └── kfxlib/          <- copy here
   │       ├── __init__.py
   │       ├── yj_book.py
   │       └── ... (other files)
   ```

**Alternative:** Set environment variable:
```bash
# Windows (PowerShell)
$env:KFX_PLUGIN_DIR = "C:\path\to\kfx_plugin"

# Linux/macOS
export KFX_PLUGIN_DIR="/path/to/kfx_plugin"
```

## Usage

### GUI Mode (recommended for beginners)

```bash
python nbk_convert.py --gui
```

The GUI provides:
- 📁 Path selection for notebook root directory
- 🔍 Notebook scan with PDF name preview
- 🎯 Selective conversion of individual or multiple notebooks
- 📱 Kindle MTP connection (Windows)
- ⚙️ Options for `Skip Existing`, `Use Clean Title`

### Command-Line Interface (CLI)

#### Convert single file

```bash
python nbk_convert.py <path-to-nbk-or-directory> [output.pdf]
```

**Examples:**

```bash
# Direct NBK file
python nbk_convert.py /path/to/notebooks/notebook-dir/nbk output.pdf

# Notebook directory (PDF created next to nbk file)
python nbk_convert.py /path/to/notebooks/notebook-dir/
```

#### Batch conversion

```bash
# Convert all notebooks recursively under a directory
python nbk_convert.py /path/to/notebooks --batch

# With separate output directory
python nbk_convert.py /path/to/notebooks --batch /path/to/output

# Skip existing PDFs
python nbk_convert.py /path/to/notebooks --batch --skip-existing

# Use clean titles (from notebook metadata) instead of UUIDs
python nbk_convert.py /path/to/notebooks --batch --use-title

# Preview without conversion
python nbk_convert.py /path/to/notebooks --batch --dry-run

# Combined
python nbk_convert.py /path/to/notebooks --batch --skip-existing --use-title --plugin-dir /path/to/kfx_plugin
```

#### Custom KFX plugin directory

```bash
python nbk_convert.py /path/to/input --plugin-dir /path/to/kfx_plugin
```

## NBK File Structure

Kindle Scribe notebooks are stored as directories:

```
<UUID-or-ASIN>!!PDOC!!notebook/
├── nbk                 <- Main file (SQLite + Ion fragments)
├── nbk-journal         <- Write-Ahead Log
└── [other files]
```

The project can:
- ✅ Accept **file paths** (e.g., `~/notebooks/abc/nbk`)
- ✅ Accept **directory paths** (e.g., `~/notebooks/abc/`)
- ✅ Search **root paths** (e.g., `~/notebooks/` finds all NBK files recursively)

## Kindle Sync (Windows)

### Automatic Detection

The program automatically attempts to detect a connected Kindle Scribe via MTP:

```bash
python nbk_convert.py --gui
# Click "Connect Kindle" — finds the notebook partition
```

### Manual MTP Sync

```python
from nbk_convert import sync_kindle_notebooks_via_mtp

# Copy notebooks from Kindle to local disk
local_root, copied = sync_kindle_notebooks_via_mtp(
    device_name="Kindle Scribe",
    target_root="D:\\kindle_cache"
)
print(f"Copied {copied} files to {local_root}")
```

**Requirements:**
- Windows 11+
- Kindle Scribe connected via USB
- MTP driver installed (usually automatic)

## Directory Structure

```
kindle_notebook_pdf_converter/
├── README.md                          <- This file
├── setup.py                           <- Installs Python deps and kfxlib
├── pyproject.toml                     <- Project metadata
├── requirements.txt                   <- Python dependencies
├── .venv/                             <- Virtual environment
├── kfx_plugin/
│   └── kfxlib/                        <- Auto-downloaded KFX plugin
├── nbk_convert.py                     <- Main converter / GUI entry point
├── kindle_mtp_cache/                  <- MTP sync output
├── notebooks/                         <- Local notebook collection
└── docs/                              <- Additional documentation
```

## Output

Generated PDFs contain:

- ✅ All strokes with exact color and thickness
- ✅ Light gray background lines (simulated lined notebook template)
- ✅ Transparent markers/highlighters (20% opacity)
- ✅ Vector graphics (scalable, not pixelated)

**Coordinate system:**
- Canvas units: sub-pixel at nominal **2520 PPI**
- PDF page size: matches Kindle Scribe screen size

## Dependencies in Detail

| Package    | Version | Purpose                                     |
|-----------|---------|---------------------------------------------|
| **reportlab** | ≥4.0.0  | PDF generation and vector rendering        |
| **pypdf**     | ≥3.0.0  | PDF handling (required by kfxlib)         |
| **lxml**      | ≥4.9.0  | XML processing (required by kfxlib)       |
| **Pillow**    | ≥9.0.0  | Image processing (required by kfxlib)     |
| **beautifulsoup4** | ≥4.12.0 | HTML/XML parsing used by kfxlib      |
| **kfxlib**    | local   | Kindle format decoding (GPL v3)            |

## Troubleshooting

### "kfxlib not found"

```
ImportError: No module named 'kfxlib'
```

**Solution:**
- Run `py setup.py` again to trigger automatic download and registration
- Verify that `kfxlib/` exists in `kfx_plugin/`
- Or set `KFX_PLUGIN_DIR`:
  ```bash
  export KFX_PLUGIN_DIR="/path/to/kfx_plugin"
  python nbk_convert.py ...
  ```

### "BeautifulSoup module is missing"

This means `beautifulsoup4` is missing from the active Python environment.

**Solution:**
- Re-run `py setup.py`
- Or install manually with `pip install beautifulsoup4>=4.12.0`

### "nbk file not found"

```
FileNotFoundError: No 'nbk' file found in directory
```

**Solution:**
- Verify that the notebook directory contains a file named `nbk` (no extension!)
- On Windows: display `nbk` with `dir /A`
- Full path required: `D:\notebooks\<UUID>!!PDOC!!notebook\nbk`

### "MTP device not found"

```
RuntimeError: MTP device 'Kindle Scribe' not found
```

**Solution:**
- Connect Kindle via USB
- Check device name (`"Kindle Scribe"` or `"Kindle"`)
- Update MTP driver in Windows

### "Warning: File not recognized as Scribe notebook"

- The file may not be convertible
- Check the NBK structure

## License

- **This project:** MIT or similar
- **kfxlib:** GPL v3 (© John Howell) — linked at runtime
- **ReportLab:** BSD License

## Support & Additional Help

1. **GUI won't start** → Check Tk installation:
   ```bash
   python -m tkinter  # should open a window
   ```

2. **"Invalid signature"** in stroke decoding → NBK file may be corrupted

3. **Slow conversion** → Use batch mode or set up multiple workers

## Development

See docstrings in `nbk_convert.py` for API details:

```python
from nbk_convert import convert, extract_pages

# Programmatic conversion
stats = convert(
    input_path="/path/to/nbk",
    output_path="output.pdf",
    plugin_dir="/path/to/kfx_plugin"
)
print(f"{stats['n_pages']} pages, {stats['n_strokes']} strokes")
```

---

## Disclaimer

This project is not affiliated with Amazon or Kindle. Kindle and Kindle Scribe are trademarks of Amazon.

**Last updated:** April 2026
