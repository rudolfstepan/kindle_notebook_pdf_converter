# Architecture

## Project Structure

```
kindle_notebook_pdf_converter/
├── .github/              # GitHub Actions, templates
├── docs/                 # Documentation
├── tests/                # Test suite
├── scripts/              # Utility scripts
├── nbk_convert.py        # Main converter script
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── setup.py              # Package setup
└── pyproject.toml        # Modern Python config
```

## Components

### 1. NBK File Handling (`nbk_convert.py`)

**Purpose:** Load and parse Kindle Scribe notebook files

**Key Functions:**
- `resolve_nbk_input()` - Locate NBK files in filesystem
- `find_all_nbk_dirs()` - Discover notebooks recursively
- `YJ_Book` - kfxlib class for decoding Ion fragments

**Flow:**
```
NBK File (SQLite + Ion)
    ↓
kfxlib.YJ_Book
    ↓
Fragment Graph Traversal
    ↓
Page/Stroke Extraction
```

### 2. Stroke Decoding (`decode_stroke_values()`)

**Purpose:** Decompress delta-of-delta-encoded coordinates

**Algorithm:**
- Read 4-bit nibble instructions
- Apply variable-length operands
- Reconstruct second-order deltas

**Output:** Absolute canvas coordinates (sub-pixels at 2520 PPI)

### 3. PDF Rendering (`render_pdf()`)

**Purpose:** Generate vector PDF from stroke data

**ReportLab Pipeline:**
1. Create canvas at exact Kindle Scribe resolution
2. Draw background guide lines
3. Render each stroke as path
4. Apply colors and opacity
5. Save to PDF

**Coordinate System:**
- Canvas: Origin at top-left, Y increases downward
- PDF: Origin at bottom-left, Y increases upward
- Conversion: `pdf_y = page_height - (canvas_y / ppi * 72)`

### 4. Title Extraction (`extract_nbk_title()`)

**Priority:**
1. Metadata (`$490` fragment) - explicit title from book
2. Directory name - ASIN/hash pattern
3. UUID fallback - raw directory name

### 5. GUI Application (`run_gui()`)

**Stack:** Tkinter (built-in, cross-platform)

**Architecture:**
- Main thread: UI event loop
- Worker threads: Long-running tasks (scan, convert, MTP sync)
- Event queue: Thread-safe communication

**Workflow:**
```
User Input
    ↓
Main Thread (Tk)
    ↓
Worker Thread Pool
    ↓
Event Queue
    ↓
Main Thread (UI Update)
```

### 6. Kindle MTP Sync (`sync_kindle_notebooks_via_mtp()`)

**Windows-specific:** Uses COM Shell API via PowerShell

**Process:**
1. Detect device via Shell.Application
2. Navigate to .notebooks directory
3. Recursively copy files to local cache
4. Poll for completion (timeout: 120s)

## Data Flow

### Single Conversion

```
Input Path
    ↓
resolve_nbk_input()
    ↓
Create temp directory + copy NBK
    ↓
YJ_Book.decode_book()
    ↓
extract_pages()
    ├─ Walk fragment graph
    ├─ Decode strokes
    └─ Collect pages
    ↓
render_pdf()
    ├─ Create canvas
    ├─ Draw lines
    └─ Draw strokes
    ↓
Output PDF
```

### Batch Conversion

```
Root Directory
    ↓
find_all_nbk_dirs()
    ├─ os.walk()
    └─ Collect all NBK files
    ↓
For each notebook:
    ├─ Single Conversion Flow (above)
    ├─ Handle errors gracefully
    └─ Report statistics
    ↓
Summary Statistics
```

## Dependencies

### Core Runtime

| Package    | Role                        | Why                                    |
|-----------|------------------------------|----------------------------------------|
| reportlab | PDF generation              | Vector graphics, precise output       |
| pypdf     | PDF utilities               | Required by kfxlib                    |
| lxml      | XML parsing                 | Required by kfxlib                    |
| Pillow    | Image processing            | Required by kfxlib                    |
| kfxlib    | Kindle format decoding      | Core functionality (external, GPL v3) |

### Development

- **pytest** - Testing framework
- **black** - Code formatting
- **pylint** - Linting
- **mypy** - Type checking
- **sphinx** - Documentation generation

## Threading Model

### GUI Mode

```
Main Thread (Tkinter)
    ├─ Event loop
    ├─ UI rendering
    └─ Event drain (every 120ms)
        ↓
    Worker Threads
        ├─ Notebook scanning
        ├─ Conversion
        └─ MTP sync
            ↓
        Event Queue
            ↓
        Main Thread (UI Update)
```

### Key Points

- Workers are daemon threads (don't block exit)
- Queue.Queue provides thread-safe communication
- Progress updates via (event_type, payload) tuples
- Graceful error handling without blocking UI

## Error Handling

### NBK Parsing Errors

```python
try:
    book.decode_book()
except Exception as e:
    # Log and skip, continue with next notebook
```

### Stroke Decoding Errors

```python
try:
    xs = decode_stroke_values(data, num_points, "x")
except ValueError as e:
    # Skip stroke, log warning, continue
```

### File I/O Errors

```python
try:
    convert(input_path, output_path, plugin_dir)
except Exception as e:
    # Log error, increment fail_count, continue batch
```

## Performance Considerations

### Optimization Opportunities

1. **Parallel Batch Processing** - Convert multiple notebooks simultaneously
2. **Progressive Rendering** - Stream PDF output instead of buffering
3. **Stroke Simplification** - Reduce points for smoother, smaller PDFs
4. **Caching** - Cache decoded pages during preview

### Benchmarks

- Typical notebook: 50-200 pages, 200-2000 strokes
- Single page rendering: ~50-200ms
- Full notebook PDF: 2-10 seconds
- Batch mode: Linear with count

---

See also: [Usage Guide](usage.md), [Installation](installation.md)
