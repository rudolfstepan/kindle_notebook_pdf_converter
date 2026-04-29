# Kindle Scribe Notebook PDF Converter

Converts handwritten notes from Kindle Scribe (`.nbk` files) to PDFs with full vector rendering of strokes.

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
cd downloader
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
```

### 4. Prepare KFX Plugin

The project requires the `kfxlib` library from John Howell's **Calibre KFX Input Plugin**:

1. Download the [KFX Input Plugin](https://www.mobileread.com/forums/showthread.php?t=272713)
2. Extract the ZIP file
3. Navigate to the directory containing `kfxlib/`
4. Copy the `kfxlib` folder to the `kfx_plugin/` directory:
   ```
   downloader/
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
python kindle_notebook_pdf_converter/nbk_convert.py --gui
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
cd kindle_notebook_pdf_converter
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
python nbk_convert.py /path/to/notebooks --batch --output /path/to/output

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
from kindle_notebook_pdf_converter.nbk_convert import sync_kindle_notebooks_via_mtp

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
downloader/
├── README.md                          <- This file
├── requirements.txt                   <- Python dependencies
├── .venv/                             <- Virtual environment
├── kfx_plugin/
│   └── kfxlib/                        <- KFX Plugin (external)
├── kindle_notebook_pdf_converter/
│   ├── nbk_convert.py                 <- Main script
│   ├── nbk_convert.py                 
│   ├── kindle_mtp_cache/              <- MTP sync cache
│   └── notebooks/                     <- Sample notebooks
├── kindle_mtp_cache/                  <- MTP sync output
├── kfx_plugin/                        <- KFX Plugin
├── notebooks/                         <- Local notebook collection
└── [other tools]
    ├── video_link_scanner.py
    ├── convert_nbk_to_pdf.py
    └── kindle_scribe_calibre_import.py
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
| **kfxlib**    | local   | Kindle format decoding (GPL v3)            |

## Troubleshooting

### "kfxlib not found"

```
ImportError: No module named 'kfxlib'
```

**Solution:**
- Verify that `kfxlib/` exists in `kfx_plugin/`
- Or set `KFX_PLUGIN_DIR`:
  ```bash
  export KFX_PLUGIN_DIR="/path/to/kfx_plugin"
  python nbk_convert.py ...
  ```

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
from kindle_notebook_pdf_converter.nbk_convert import convert, extract_pages

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
