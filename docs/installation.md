# Installation Guide

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning)
- Windows 11+ (for MTP sync feature)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/downloader.git
cd downloader/kindle_notebook_pdf_converter
```

### 2. Create Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
& .\.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate.bat

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install KFX Plugin

The project requires `kfxlib` from John Howell's Calibre KFX Input plugin.

#### Option A: Download & Extract

1. Download [KFX Input Plugin](https://www.mobileread.com/forums/showthread.php?t=272713)
2. Extract the ZIP file
3. Copy the `kfxlib` folder to:
   ```
   kindle_notebook_pdf_converter/kfx_plugin/kfxlib/
   ```

#### Option B: Environment Variable

If `kfxlib` is located elsewhere:

```bash
# Windows (PowerShell)
$env:KFX_PLUGIN_DIR = "C:\path\to\kfx_plugin"

# Windows (Command Prompt)
set KFX_PLUGIN_DIR=C:\path\to\kfx_plugin

# macOS/Linux
export KFX_PLUGIN_DIR="/path/to/kfx_plugin"
```

### 5. Verify Installation

```bash
python nbk_convert.py --help
```

Should display the help message without errors.

## Installation for Development

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Quality Checks

```bash
# Format code
black nbk_convert.py

# Lint
pylint nbk_convert.py

# Type checking
mypy nbk_convert.py
```

## Platform-Specific Notes

### Windows

- MTP sync requires Windows 11+ (uses PowerShell COM APIs)
- PowerShell execution policy may need adjustment:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
  ```

### macOS

- Install Python via Homebrew (recommended):
  ```bash
  brew install python@3.11
  ```
- MTP sync not supported (no native MTP driver)

### Linux

- Install Python:
  ```bash
  sudo apt-get install python3.11 python3.11-venv
  ```
- MTP sync requires `python3-gi` and `gobject-introspection`:
  ```bash
  sudo apt-get install python3-gi gir1.2-gvfs-1.0
  ```

## Package Installation

### Install from Source

```bash
cd kindle_notebook_pdf_converter
pip install -e .
```

This installs the package in development mode (`-e` flag).

### Install from Wheel

```bash
python -m build --wheel
pip install dist/kindle_notebook_converter-1.0.0-py3-none-any.whl
```

## Troubleshooting

### "kfxlib not found"

```
ModuleNotFoundError: No module named 'kfxlib'
```

**Solution:**
1. Verify `kfx_plugin/kfxlib/` exists
2. Check `__init__.py` exists in `kfxlib/`
3. Set `KFX_PLUGIN_DIR` environment variable

### "Python version not supported"

```
ERROR: Package requires Python >=3.8
```

**Solution:**
```bash
# Check version
python --version

# Install correct Python version
# Visit https://www.python.org/downloads/
```

### "Permission denied" (Linux/macOS)

```bash
# Add execute permission
chmod +x nbk_convert.py
```

### Virtual Environment not activating

```bash
# Windows: Use full path
& "C:\path\to\.venv\Scripts\Activate.ps1"

# macOS/Linux: Use source
source /path/to/.venv/bin/activate
```

## Updating

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Update Entire Project

```bash
git pull origin main
pip install --upgrade -r requirements.txt
```

## Next Steps

- [Usage Guide](usage.md)
- [Examples](../examples/)
- [Contributing](../CONTRIBUTING.md)

---

See also: [README](../README.md), [Architecture](architecture.md)
