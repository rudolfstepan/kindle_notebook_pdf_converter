#!/usr/bin/env python3
"""
nbk_convert.py — Convert Kindle Scribe handwritten notebook files (.nbk) to PDF.

Overview
--------
The Kindle Scribe stores every notebook as a directory containing two binary
files named ``nbk`` (the main SQLite/Ion container) and ``nbk-journal`` (a
write-ahead log).  Neither file carries an extension.

This script opens the ``nbk`` container via the ``kfxlib`` library — the core
logic of John Howell's Calibre KFX Input plugin (GPL v3) — deserialises the
Amazon Ion fragments stored inside, extracts all handwritten stroke data, and
renders them as vector paths into a PDF using ReportLab.

Dependencies
------------
- **kfxlib** — extracted from the Calibre "KFX Input" plugin ZIP.
  Default search path: ``<script dir>/kfx_plugin/kfxlib``.
  Override with the environment variable ``KFX_PLUGIN_DIR``.
- **reportlab** — PDF generation (``pip install reportlab``)
- **pypdf**    — required by kfxlib   (``pip install pypdf``)
- **lxml**     — required by kfxlib   (``pip install lxml``)
- **Pillow**   — required by kfxlib   (``pip install Pillow``)

Usage
-----
  # Single notebook directory or nbk file:
  python nbk_convert.py <input> [output.pdf]

  # Batch-convert all notebooks found recursively under a root directory:
  python nbk_convert.py <root> --batch [output_dir]

  # Batch dry-run (preview without writing):
  python nbk_convert.py <root> --batch --dry-run

  # Batch, skip already-converted notebooks:
  python nbk_convert.py <root> --batch --skip-existing

  # Specify a custom kfxlib directory:
  python nbk_convert.py <root> --batch --plugin-dir path/to/kfx_plugin

NBK file format (brief)
-----------------------
The ``nbk`` file is a SQLite database whose rows contain Amazon Ion-encoded
fragments.  Each fragment belongs to a typed category (``ftype``) and is
identified by a unique ID (``fid``).  The notebook model (``nmdl.*``) namespace
defines pages, strokes, stroke-point arrays, and metadata.

Stroke coordinates are stored as delta-of-delta-encoded 4-bit instruction
streams (see ``decode_stroke_values``) and reference a canvas coordinate space
measured in sub-pixels at a nominal PPI of 2520.

License note
------------
kfxlib is © John Howell, licensed under the GNU General Public License v3.
This script is a standalone converter that links against it at runtime.
"""

from __future__ import annotations
import argparse
import threading
import queue
import os
import re
import sys
import shutil
import tempfile
import json
import subprocess
from datetime import datetime

# ----------------------------------------------------------------------------
# Logger-Stub für das KFX-Plugin
# ----------------------------------------------------------------------------
class _NullLog:
    """Silent logger passed to kfxlib to suppress all plugin console output.

    kfxlib calls ``set_logger`` with an object that exposes ``info``,
    ``warning``, ``error``, and ``debug`` methods.  Providing no-op
    implementations keeps the converter output clean.
    """

    def info(self, _msg): pass
    def warning(self, _msg): pass
    def error(self, _msg): pass
    def debug(self, _msg): pass


def _setup_kfx_plugin(plugin_dir: str) -> None:
    """Insert the kfxlib directory into ``sys.path`` and silence the plugin logger.

    Must be called once before any ``from kfxlib...`` import.  Subsequent calls
    are safe because ``sys.path`` insertion is idempotent for the same path.

    Args:
        plugin_dir: Absolute path to the directory that *contains* the
                    ``kfxlib`` package (i.e. the directory where
                    ``kfxlib/__init__.py`` lives).

    Raises:
        ImportError: If ``kfxlib`` cannot be found under ``plugin_dir``.
    """
    sys.path.insert(0, plugin_dir)
    from kfxlib.message_logging import set_logger
    set_logger(_NullLog())


# ----------------------------------------------------------------------------
# Stroke-Wertedekoder (aus yj_to_epub_notebook.decode_stroke_values portiert)
# ----------------------------------------------------------------------------
def decode_stroke_values(data: bytes, num_points: int, name: str = "") -> list[int]:
    """Decode a delta-of-delta-encoded stroke coordinate array from raw bytes.

    The Kindle Scribe firmware stores every X and Y coordinate array in a
    compact variable-length encoding to minimise storage.  The algorithm uses
    a second-order delta scheme: rather than storing raw coordinates, it stores
    the change-of-change between successive values, which is typically very
    small for smooth pen strokes.

    Binary layout
    ~~~~~~~~~~~~~
    ::

        [0x01 0x01]          2-byte magic signature
        [uint32-LE]          number of encoded values (num_vals)
        [nibble stream ...]  two 4-bit instructions packed per byte
        [increment bytes ...] variable-length operand bytes consumed by the
                             nibble instructions

    Each 4-bit nibble instruction encodes:

    - Bits 0-1 (``n``): operand width selector

      - ``0`` → increment is 0 (no bytes consumed)
      - ``1`` → 1-byte unsigned increment
      - ``2`` → 2-byte little-endian unsigned increment
      - ``3`` → 3-byte little-endian unsigned increment

    - Bit 2: if set, ``n`` itself is the increment (no operand bytes consumed)
    - Bit 3: if set, negate the increment

    Reconstruction::

        change[0] = 0;  value[0] = increment[0]
        change[i] = change[i-1] + increment[i]
        value[i]  = value[i-1]  + change[i]

    Args:
        data:       Raw bytes of the ``nmdl.position_x`` or
                    ``nmdl.position_y`` Ion blob field.
        num_points: Expected number of decoded values (from
                    ``nmdl.num_points``).  If the stored count differs, it
                    is silently overridden by this value.
        name:       Optional label used in error messages (e.g. ``"x"`` or
                    ``"y"``) to ease debugging.

    Returns:
        A list of ``num_points`` integer coordinate values in canvas units.

    Raises:
        ValueError: If the two-byte magic signature is not ``0x01 0x01``.
    """
    import struct

    pos = 0
    if data[pos:pos+2] != b"\x01\x01":
        raise ValueError(f"{name}: ungültige Signatur {data[:2].hex()}")
    pos += 2
    num_vals = struct.unpack("<I", data[pos:pos+4])[0]
    pos += 4
    if num_vals != num_points:
        # Plugin loggt nur, wir akzeptieren leise.
        num_vals = num_points

    # Instruktionen einsammeln (zwei 4-Bit-Nibbles pro Byte)
    instrs = []
    instr_pos = pos
    while len(instrs) < num_vals:
        if instr_pos >= len(data):
            break
        b = data[instr_pos]
        instr_pos += 1
        instrs.append(b >> 4)
        instrs.append(b & 0x0F)
    if len(instrs) > num_vals:
        instrs.pop()  # Padding-Nibble entfernen
    pos = instr_pos

    vals = []
    change = 0
    value = 0
    for i in range(num_vals):
        instr = instrs[i] if i < len(instrs) else 0
        n = instr & 3
        if instr & 4:
            increment = n
        else:
            if n == 0:
                increment = 0
            elif n == 1:
                increment = data[pos]; pos += 1
            elif n == 2:
                increment = struct.unpack("<H", data[pos:pos+2])[0]; pos += 2
            else:
                increment = data[pos] | (struct.unpack("<H", data[pos+1:pos+3])[0] << 8)
                pos += 3
        if instr & 8:
            increment = -increment

        if i == 0:
            change = 0
            value = increment
        else:
            change += increment
            value += change
        vals.append(value)
    return vals


# ----------------------------------------------------------------------------
# Pages aus dem Plugin-Buch extrahieren
# ----------------------------------------------------------------------------
def extract_pages(book) -> list[dict]:
    """Extract page and stroke data from a decoded kfxlib YJ_Book object.

    Walks the Ion fragment graph in reading order, collecting every stroke on
    every page.  Stroke coordinates are decoded from their delta-of-delta
    encoding and translated from local (bounding-box-relative) to absolute
    canvas coordinates.

    Fragment traversal
    ~~~~~~~~~~~~~~~~~~
    The book's reading-order fragment (``ftype == "$258"``) provides an ordered
    list of page fragment IDs.  Each page fragment contains a list of top-level
    content items (field ``$141``).  Items are recursively walked via
    ``walk_strokes``:

    - If an item has ``nmdl.type == "nmdl.stroke"`` or contains the key
      ``nmdl.stroke_points``, it is treated as a leaf stroke node.
    - Otherwise the walker follows referenced sub-sections (field ``$176``) and
      inline children (field ``$146``).

    Coordinate system
    ~~~~~~~~~~~~~~~~~
    All canvas coordinates are in sub-pixel units at the page's normalised PPI
    (typically 2520).  Each stroke stores an origin bounding-box offset
    (``nmdl.stroke_bounds[0]``, ``nmdl.stroke_bounds[1]``); decoded X/Y values
    are relative to this offset and must be shifted to absolute canvas space.

    Args:
        book: A fully decoded ``kfxlib.yj_book.YJ_Book`` instance whose
              ``fragments`` attribute is populated.

    Returns:
        A list of page dicts, one per page in reading order.  Each dict has:

        - ``canvas_w`` (int): page width in canvas units
        - ``canvas_h`` (int): page height in canvas units
        - ``ppi`` (float): normalised pixels-per-inch of the canvas
        - ``strokes`` (list[dict]): strokes on this page, each containing:

          - ``xs`` (list[int]): absolute X coordinates
          - ``ys`` (list[int]): absolute Y coordinates
          - ``thickness`` (float): pen width in canvas units
          - ``color`` (int): 24-bit RGB packed integer
          - ``brush_type`` (int): ``1`` = highlighter, ``7`` = ballpoint, etc.
    """
    from kfxlib.ion import IonAnnotation

    def unwrap(v):
        while isinstance(v, IonAnnotation):
            v = v.value
        return v

    frag_by_id = {f.fid: f for f in book.fragments}

    def walk_strokes(item):
        item = unwrap(item)
        nmdl_type = item.get("nmdl.type")
        if nmdl_type == "nmdl.stroke" or "nmdl.stroke_points" in item:
            yield item
            return
        # Sub-Section
        ref = item.get("$176")
        if ref and ref in frag_by_id:
            sub = frag_by_id[ref].value
            for c in sub.get("$146", []):
                yield from walk_strokes(c)
        # Inline-Children
        for c in item.get("$146", []):
            yield from walk_strokes(c)

    reading_order = next(f for f in book.fragments if f.ftype == "$258")
    page_ids = list(reading_order.value["$169"][0]["$170"])

    pages = []
    for pid in page_ids:
        pf = frag_by_id[pid].value
        canvas_w = int(pf.get("nmdl.canvas_width", 15624))
        canvas_h = int(pf.get("nmdl.canvas_height", 20832))
        ppi = float(pf.get("nmdl.normalized_ppi", 2520.0))

        strokes = []
        for top_item in pf.get("$141", []):
            for s in walk_strokes(top_item):
                pts = s.get("nmdl.stroke_points", {})
                npts = int(pts.get("nmdl.num_points", 0))
                if npts < 1:
                    continue
                bx, by = int(s["nmdl.stroke_bounds"][0]), int(s["nmdl.stroke_bounds"][1])
                try:
                    xs = decode_stroke_values(bytes(pts["nmdl.position_x"]), npts, "x")
                    ys = decode_stroke_values(bytes(pts["nmdl.position_y"]), npts, "y")
                except Exception as e:
                    print(f"  Skip stroke: {e}", file=sys.stderr)
                    continue
                xs = [v + bx for v in xs]
                ys = [v + by for v in ys]
                strokes.append({
                    "xs": xs,
                    "ys": ys,
                    "thickness": float(s.get("nmdl.thickness", 23.625)),
                    "color": int(s.get("nmdl.color", 0)),
                    "brush_type": int(s.get("nmdl.brush_type", 7)),
                })
        pages.append({
            "canvas_w": canvas_w,
            "canvas_h": canvas_h,
            "ppi": ppi,
            "strokes": strokes,
        })
    return pages


# ----------------------------------------------------------------------------
# PDF-Renderer (reportlab)
# ----------------------------------------------------------------------------
def render_pdf(pages: list[dict], output_path: str) -> None:
    """Render extracted page/stroke data as a vector PDF using ReportLab.

    Each page is drawn on a separate PDF page whose physical dimensions match
    the Scribe canvas exactly (canvas units converted to PostScript points via
    ``points = canvas_units / ppi * 72``).

    Rendering pipeline per page
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1. **Background guide lines** — light grey horizontal lines are drawn at
       evenly spaced intervals (~28 lines per page) to suggest the lined
       notebook template.  They do not represent actual template data from the
       device.
    2. **Strokes** — each stroke is rendered as an open vector path.
       Single-point strokes (only one coordinate pair) are rendered as filled
       circles instead.
    3. **Brush types** — brush type ``1`` (highlighter) is drawn with 20%
       opacity; all other types are fully opaque.
    4. **Line caps/joins** are set to round (``setLineCap(1)``,
       ``setLineJoin(1)``) for smooth pen appearance.

    Coordinate conversion
    ~~~~~~~~~~~~~~~~~~~~~
    Canvas Y coordinates increase downward; PDF Y coordinates increase upward.
    The vertical flip is applied as::

        pdf_y = page_height_pt - (canvas_y / ppi * 72)

    Args:
        pages:       Output of :func:`extract_pages` — a list of page dicts.
        output_path: Destination file path for the generated PDF.

    Raises:
        ValueError: If ``pages`` is empty.
    """
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.colors import Color

    if not pages:
        raise ValueError("No pages to render")

    # Erste Seite definiert PDF-Pagesize
    first = pages[0]
    page_w_pt = first["canvas_w"] / first["ppi"] * 72.0
    page_h_pt = first["canvas_h"] / first["ppi"] * 72.0

    c = rl_canvas.Canvas(output_path, pagesize=(page_w_pt, page_h_pt))
    c.setLineCap(1)   # rund
    c.setLineJoin(1)  # rund

    for page in pages:
        ppi = page["ppi"]
        cw, ch = page["canvas_w"], page["canvas_h"]
        page_w = cw / ppi * 72.0
        page_h = ch / ppi * 72.0
        c.setPageSize((page_w, page_h))

        # Helle Hintergrundlinien als Andeutung des Notebook-Templates
        c.setStrokeColor(Color(0.92, 0.92, 0.92))
        c.setLineWidth(0.4)
        line_spacing_pt = (2520 / ppi) * 72.0 / 28  # ca. 28 Zeilen
        for i in range(1, int(page_h / line_spacing_pt)):
            y = page_h - i * line_spacing_pt
            c.line(20, y, page_w - 20, y)

        # Strokes
        for s in page["strokes"]:
            color_int = s["color"] & 0xFFFFFF
            r = ((color_int >> 16) & 0xFF) / 255.0
            g = ((color_int >> 8) & 0xFF) / 255.0
            b = (color_int & 0xFF) / 255.0
            c.setStrokeColor(Color(r, g, b))

            lw_pt = s["thickness"] / ppi * 72.0
            c.setLineWidth(max(0.3, lw_pt))

            # Highlighter (brush_type 1) leicht transparent
            if s["brush_type"] == 1:
                c.setStrokeColor(Color(r, g, b, alpha=0.2))

            xs, ys = s["xs"], s["ys"]
            if len(xs) < 2:
                # Einzelner Punkt → kleiner Kreis
                px = xs[0] / ppi * 72.0
                py = page_h - (ys[0] / ppi * 72.0)
                c.circle(px, py, max(0.3, lw_pt) / 2.0, stroke=0, fill=1)
                continue

            path = c.beginPath()
            px0 = xs[0] / ppi * 72.0
            py0 = page_h - (ys[0] / ppi * 72.0)
            path.moveTo(px0, py0)
            for i in range(1, len(xs)):
                px = xs[i] / ppi * 72.0
                py = page_h - (ys[i] / ppi * 72.0)
                path.lineTo(px, py)
            c.drawPath(path, stroke=1, fill=0)

        c.showPage()

    c.save()


# ----------------------------------------------------------------------------
# Title extraction
# ----------------------------------------------------------------------------

_SAFE_CHARS_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _safe_filename(name: str, max_len: int = 120) -> str:
    """Sanitise a string so it can be used as a file-system name.

    Replaces characters that are illegal on Windows/macOS/Linux with an
    underscore and truncates to *max_len* characters.
    """
    safe = _SAFE_CHARS_RE.sub("_", name).strip('. ')
    return safe[:max_len] if safe else "_"


def extract_nbk_title(nbk_file: str, plugin_dir: str, dir_name: str) -> str:
    """Derive a human-readable title for a Kindle Scribe notebook.

    Title resolution priority
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    1. **``kindle_title_metadata/title``** stored inside the ``$490`` Ion
       fragment of the NBK file.  This is set for book-annotation notebooks
       when the device has the book title available.
    2. **Directory-name ASIN** — for directories whose names follow the
       pattern ``<ASIN>!!EBOK!!notebook`` or ``<hash>!!PDOC!!notebook``, the
       first segment (ASIN / document hash) is used as a recognisable
       identifier that can be cross-referenced with the user's library.
    3. **UUID fallback** — for purely standalone notebooks where no title
       exists, the raw UUID directory name is returned unchanged.

    Args:
        nbk_file:   Absolute path to the ``nbk`` binary file.
        plugin_dir: Directory containing the ``kfxlib`` package.
        dir_name:   Name of the notebook's parent directory (used for
                    pattern-based extraction without opening the file).

    Returns:
        A sanitised string suitable for use as a PDF filename stem.
    """
    # --- Priority 2: quick parse from directory name (no file I/O needed) ---
    # Patterns: "<ID>!!EBOK!!notebook" or "<ID>!!PDOC!!notebook"
    dir_match = re.match(r'^([A-Za-z0-9_-]+)!!(EBOK|PDOC)!!notebook$', dir_name)
    dir_id = dir_match.group(1) if dir_match else None
    doc_type = dir_match.group(2) if dir_match else None

    # --- Priority 1: read $490 fragment from NBK for explicit title ---
    try:
        _setup_kfx_plugin(plugin_dir)
        from kfxlib.yj_book import YJ_Book

        with tempfile.TemporaryDirectory() as tmp:
            shutil.copyfile(nbk_file, os.path.join(tmp, "nbk"))
            book = YJ_Book(tmp)
            book.decode_book(set_metadata=None, set_approximate_pages=None)

        meta_frag = next((f for f in book.fragments if str(f.ftype) == "$490"), None)
        if meta_frag is not None:
            # Traverse: $491 list -> each entry has $495 (category) and $258 (items)
            # Items have $492 (key) and $307 (value)
            outer = meta_frag.value
            entries = outer.get("$491", [])
            for entry in entries:
                category = str(entry.get("$495", ""))
                if category != "kindle_title_metadata":
                    continue
                for kv in entry.get("$258", []):
                    key = str(kv.get("$492", ""))
                    val = kv.get("$307")
                    if key == "title" and val:
                        return _safe_filename(str(val))
    except Exception:
        pass  # Fall through to lower-priority sources

    # --- Priority 2 result: use ASIN/hash from directory name ---
    if dir_id:
        label = f"{dir_id}_{doc_type}" if doc_type else dir_id
        return _safe_filename(label)

    # --- Priority 3: raw UUID directory name ---
    return _safe_filename(dir_name)


# ----------------------------------------------------------------------------
# Hauptablauf
# ----------------------------------------------------------------------------
def convert(input_path: str, output_path: str, plugin_dir: str) -> dict:
    """Convert a single ``nbk`` file to a PDF and return conversion statistics.

    This is the main entry point for single-file conversion.  It orchestrates
    the full pipeline: kfxlib setup → book decoding → stroke extraction → PDF
    rendering.

    The kfxlib ``YJ_Book`` loader expects the ``nbk`` file to be named exactly
    ``nbk`` (no extension) inside a directory.  A temporary directory is used
    so that the original source file is never modified.

    Args:
        input_path: Absolute path to the ``nbk`` binary file.
        output_path: Destination path for the output PDF.
        plugin_dir:  Directory that contains the ``kfxlib`` package
                     (passed to :func:`_setup_kfx_plugin`).

    Returns:
        A dict with the following keys:

        - ``n_pages`` (int): total number of pages in the notebook
        - ``n_strokes`` (int): total number of strokes across all pages
        - ``page_strokes`` (list[int]): per-page stroke counts

    Raises:
        Any exception raised by kfxlib during decoding or by ReportLab during
        rendering is propagated to the caller unchanged.
    """
    _setup_kfx_plugin(plugin_dir)
    from kfxlib.yj_book import YJ_Book

    # Plugin erwartet die Datei im Verzeichnis als Basename "nbk"
    with tempfile.TemporaryDirectory() as tmp:
        nbk_target = os.path.join(tmp, "nbk")
        shutil.copyfile(input_path, nbk_target)

        book = YJ_Book(tmp)
        book.decode_book(set_metadata=None, set_approximate_pages=None)

        if not getattr(book, "is_scribe_notebook", False):
            print("Warnung: Datei ist nicht als Scribe-Notebook erkannt.")

        pages = extract_pages(book)

    stats = {
        "n_pages": len(pages),
        "n_strokes": sum(len(p["strokes"]) for p in pages),
        "page_strokes": [len(p["strokes"]) for p in pages],
    }
    render_pdf(pages, output_path)
    return stats


def resolve_nbk_input(path: str) -> tuple[str, str]:
    """Resolve a user-supplied path to a concrete ``nbk`` file path.

    Accepts three input forms:

    1. **Direct file path** — the path points to a file named ``nbk`` (or any
       file).  Used as-is; the default output base is the path without
       extension.
    2. **Notebook directory** — the path is a directory that contains a file
       named exactly ``nbk`` at its top level.  The default PDF output is
       placed next to the ``nbk`` file, named after the directory.
    3. **Parent directory** — the path is a directory that does *not* directly
       contain ``nbk`` but has it somewhere in its subtree.  The first match
       found by ``os.walk`` is used.

    Args:
        path: A path string pointing to an ``nbk`` file or a notebook
              directory (relative or absolute).

    Returns:
        A tuple ``(nbk_file_path, output_base)`` where ``output_base`` is the
        suggested PDF output path *without* the ``.pdf`` extension.

    Raises:
        FileNotFoundError: If no ``nbk`` file can be located at or under
                           ``path``.
    """
    p = os.path.abspath(path)
    if os.path.isdir(p):
        candidate = os.path.join(p, "nbk")
        if os.path.isfile(candidate):
            return candidate, os.path.join(p, os.path.basename(p))
        for root, _, files in os.walk(p):
            if "nbk" in files:
                found = os.path.join(root, "nbk")
                return found, os.path.join(root, os.path.basename(root))
        raise FileNotFoundError(f"Keine 'nbk'-Datei in Verzeichnis gefunden: {p}")
    if os.path.isfile(p):
        return p, os.path.splitext(p)[0]
    raise FileNotFoundError(f"Eingabe nicht gefunden: {p}")


def find_all_nbk_dirs(root: str) -> list[tuple[str, str, str]]:
    """Recursively discover all notebook directories under a root path.

    A directory is considered a notebook directory when it contains a file
    named exactly ``nbk`` (no extension).  The companion ``nbk-journal`` file
    does not need to be present.

    The default PDF output path for each notebook is placed *inside* its own
    directory, named after the directory itself (``<dir>/<dir_name>.pdf``).
    :func:`batch_convert` may override this when ``output_dir`` is set.

    Args:
        root: Root directory to search.  Relative paths are resolved to
              absolute paths before walking.

    Returns:
        A list of ``(nbk_file_path, default_pdf_path, dir_name)`` tuples, one
        per discovered notebook, in ``os.walk`` traversal order.  ``dir_name``
        is the bare directory name (not the full path) of the notebook folder.
    """
    results = []
    root_abs = os.path.abspath(root)
    for dirpath, _, files in os.walk(root_abs):
        if "nbk" in files:
            nbk_file = os.path.join(dirpath, "nbk")
            dir_name = os.path.basename(dirpath)
            pdf_path = os.path.join(dirpath, dir_name + ".pdf")
            results.append((nbk_file, pdf_path, dir_name))
    return results


def batch_convert(
    root: str,
    plugin_dir: str,
    output_dir: str | None,
    skip_existing: bool,
    dry_run: bool,
    use_title: bool,
) -> None:
    """Convert all notebooks found recursively under ``root``.

    Discovers every notebook directory via :func:`find_all_nbk_dirs` and
    invokes :func:`convert` for each one.  Failures for individual notebooks
    are caught, reported, and counted; they do not abort the batch.

    Output path resolution
    ~~~~~~~~~~~~~~~~~~~~~~
    - If ``output_dir`` is ``None``, the PDF is written next to the source
      ``nbk`` file (default behaviour of :func:`find_all_nbk_dirs`).
    - If ``output_dir`` is set, the relative sub-path of each notebook under
      ``root`` is mirrored into ``output_dir``.  Intermediate directories are
      created automatically.
    - If ``use_title`` is ``True``, :func:`extract_nbk_title` is called for
      each notebook to derive a human-readable PDF filename instead of the
      UUID directory name.  The PDF is always placed in ``output_dir`` (or
      next to the source) regardless of the original directory structure.

    Args:
        root:          Root directory to search for notebooks.
        plugin_dir:    Directory containing the ``kfxlib`` package.
        output_dir:    Optional alternative root for PDF output.  When
                       ``None``, PDFs are written next to the source files.
        skip_existing: When ``True``, any notebook whose target PDF file
                       already exists is silently skipped.
        dry_run:       When ``True``, print planned operations but do not
                       write any files or load kfxlib.
        use_title:     When ``True``, derive PDF filenames from the notebook
                       title stored inside the NBK file (via
                       :func:`extract_nbk_title`) instead of the UUID
                       directory name.
    """
    entries = find_all_nbk_dirs(root)

    if not entries:
        print(f"[HINWEIS] Keine nbk-Dateien gefunden unter: {root}")
        return

    print(f"[INFO] {len(entries)} Notebook(s) gefunden.")

    ok_count = 0
    skip_count = 0
    fail_count = 0

    for nbk_file, default_pdf, dir_name in entries:
        if use_title:
            title_stem = extract_nbk_title(nbk_file, plugin_dir, dir_name)
            base_dir = output_dir if output_dir else os.path.dirname(nbk_file)
            pdf_path = os.path.join(base_dir, title_stem + ".pdf")
        elif output_dir:
            rel = os.path.relpath(os.path.dirname(nbk_file), root)
            pdf_path = os.path.join(
                output_dir,
                rel,
                dir_name + ".pdf",
            )
        else:
            pdf_path = default_pdf

        if skip_existing and os.path.exists(pdf_path):
            print(f"[SKIP]  {pdf_path}")
            skip_count += 1
            continue

        if dry_run:
            print(f"[DRY]   {nbk_file}  ->  {pdf_path}")
            ok_count += 1
            continue

        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        try:
            stats = convert(nbk_file, pdf_path, plugin_dir)
            print(
                f"[OK]    {pdf_path}"
                f"  ({stats['n_pages']} S., {stats['n_strokes']} Strokes)"
            )
            ok_count += 1
        except Exception as exc:
            print(f"[FEHLER] {nbk_file}: {exc}", file=sys.stderr)
            fail_count += 1

    print(
        f"\n[FERTIG] Konvertiert: {ok_count}  |  "
        f"Uebersprungen: {skip_count}  |  Fehler: {fail_count}"
    )


def detect_kindle_notebook_root() -> str | None:
    """Try to locate a Kindle notebook root directory on connected drives.

    Returns the first matching path or ``None`` when no candidate exists.
    """
    env_root = os.environ.get("KINDLE_NOTEBOOKS_DIR")
    if env_root and os.path.isdir(env_root):
        return env_root

    drive_letters = [chr(code) for code in range(ord("D"), ord("Z") + 1)]
    candidates = []
    for letter in drive_letters:
        drive = f"{letter}:\\"
        if not os.path.isdir(drive):
            continue
        candidates.extend([
            os.path.join(drive, ".notebooks"),
            os.path.join(drive, "documents", ".notebooks"),
            os.path.join(drive, "notebooks"),
        ])

    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def run_powershell(script: str, env: dict[str, str] | None = None) -> str:
    """Execute a PowerShell script and return trimmed stdout.

    Raises:
        RuntimeError: If the PowerShell script exits with a non-zero code.
    """
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    if proc.returncode != 0:
        details = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(details or f"PowerShell failed with exit code {proc.returncode}")
    return (proc.stdout or "").strip()


def sync_kindle_notebooks_via_mtp(device_name: str, target_root: str) -> tuple[str, int]:
    """Copy Kindle ``.notebooks`` via MTP to a local folder.

    Args:
        device_name: MTP display name, usually "Kindle Scribe".
        target_root: Local cache root where a "notebooks" folder is created.

    Returns:
        Tuple ``(local_notebooks_root, copied_files_count)``.
    """
    if os.name != "nt":
        raise RuntimeError("MTP Kindle sync is only available on Windows")

    os.makedirs(target_root, exist_ok=True)

    ps_script = r'''
$ErrorActionPreference = "Stop"

$deviceName = $env:KINDLE_DEVICE_NAME
$targetRoot = $env:KINDLE_TARGET_ROOT
$outputRoot = Join-Path $targetRoot "notebooks"
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

$shell = New-Object -ComObject Shell.Application
$drives = $shell.NameSpace(17)
if ($null -eq $drives) {
    throw "Windows Shell Namespace konnte nicht geoeffnet werden."
}

$deviceItem = $null
foreach ($item in $drives.Items()) {
    if ($item.Name -eq $deviceName -or $item.Name -like "*$deviceName*") {
        $deviceItem = $item
        break
    }
}
if ($null -eq $deviceItem) {
    throw "MTP-Geraet '$deviceName' nicht gefunden."
}

$deviceFolder = $deviceItem.GetFolder
$internalItem = $null
foreach ($child in $deviceFolder.Items()) {
    if ($child.Name -eq "Internal Storage" -or $child.Name -like "*Storage*") {
        $internalItem = $child
        break
    }
}
if ($null -eq $internalItem) {
    throw "'Internal Storage' wurde auf '$($deviceItem.Name)' nicht gefunden."
}

$rootFolder = $internalItem.GetFolder
$notebookItem = $null
foreach ($entry in $rootFolder.Items()) {
    if ($entry.Name -eq ".notebooks" -or $entry.Name -eq "notebooks") {
        $notebookItem = $entry
        break
    }
}
if ($null -eq $notebookItem) {
    throw "'.notebooks' wurde auf dem Kindle nicht gefunden."
}

$copied = 0

function Copy-Recursive {
    param(
        [Parameter(Mandatory=$true)] $Folder,
        [string] $Prefix = ""
    )

    foreach ($entry in $Folder.Items()) {
        $name = [string]$entry.Name
        if ([string]::IsNullOrWhiteSpace($name)) {
            continue
        }

        $relativePath = if ([string]::IsNullOrEmpty($Prefix)) { $name } else { "$Prefix\\$name" }

        if ($entry.IsFolder) {
            try {
                $sub = $entry.GetFolder
                if ($null -ne $sub) {
                    Copy-Recursive -Folder $sub -Prefix $relativePath
                }
            } catch {
                # Ignore shell folder nodes that cannot be opened.
            }
            continue
        }

        $targetPath = Join-Path $outputRoot $relativePath
        $targetDir = Split-Path -Parent $targetPath
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

        $targetFolder = $shell.NameSpace($targetDir)
        if ($null -eq $targetFolder) {
            throw "Konnte Zielordner nicht oeffnen: $targetDir"
        }

        $targetFolder.CopyHere($entry, 16)

        $ok = $false
        for ($i = 0; $i -lt 120; $i++) {
            if (Test-Path -LiteralPath $targetPath) {
                $ok = $true
                break
            }
            [System.Threading.Thread]::Sleep(100)
        }
        if (-not $ok) {
            throw "Kopieren fehlgeschlagen/timeout fuer: $relativePath"
        }

        $copied++
    }
}

Copy-Recursive -Folder $notebookItem.GetFolder -Prefix ""

@{ copied = $copied; outputRoot = $outputRoot } | ConvertTo-Json -Compress
'''

    raw = run_powershell(
        ps_script,
        env={
            "KINDLE_DEVICE_NAME": device_name,
            "KINDLE_TARGET_ROOT": target_root,
        },
    )

    data = json.loads(raw) if raw else {}
    out_root = data.get("outputRoot") if isinstance(data, dict) else None
    copied = int(data.get("copied", 0)) if isinstance(data, dict) else 0

    local_root = os.path.abspath(out_root or os.path.join(target_root, "notebooks"))
    return local_root, copied


def run_gui(initial_input: str | None = None, initial_plugin_dir: str | None = None) -> None:
    """Launch the desktop UI for notebook scan and conversion.

    The GUI wraps the existing converter functions and keeps long-running tasks
    off the Tk event loop using worker threads.
    """
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class NotebookApp:
        def __init__(self, root: tk.Tk):
            self.root = root
            self.root.title("Kindle Scribe Notebook Converter")
            self.root.geometry("1140x760")
            self.root.minsize(980, 620)

            self.events: queue.Queue[tuple[str, object]] = queue.Queue()
            self.notebooks: list[tuple[str, str, str, str]] = []

            default_input = initial_input or os.path.join(os.path.dirname(os.path.abspath(__file__)), "notebooks")
            default_output = default_input
            default_plugin = initial_plugin_dir or os.environ.get(
                "KFX_PLUGIN_DIR",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "kfx_plugin"),
            )
            default_mtp_cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kindle_mtp_cache")

            self.input_var = tk.StringVar(value=default_input)
            self.output_var = tk.StringVar(value=default_output)
            self.plugin_var = tk.StringVar(value=default_plugin)
            self.mtp_cache_var = tk.StringVar(value=default_mtp_cache)
            self.device_name_var = tk.StringVar(value="Kindle Scribe")
            self.skip_existing_var = tk.BooleanVar(value=True)
            self.use_title_var = tk.BooleanVar(value=True)
            self.only_selected_var = tk.BooleanVar(value=False)

            self._build_ui(ttk)
            self.root.after(120, self._drain_events)

        def _build_ui(self, ttk_mod):
            wrapper = ttk_mod.Frame(self.root, padding=12)
            wrapper.pack(fill="both", expand=True)

            title = ttk_mod.Label(
                wrapper,
                text="Kindle Scribe Notebook Converter",
                font=("Segoe UI", 17, "bold"),
            )
            title.pack(anchor="w")

            subtitle = ttk_mod.Label(
                wrapper,
                text="Scan notebooks, preview PDF names, and convert selected or all notebooks.",
            )
            subtitle.pack(anchor="w", pady=(0, 10))

            paths = ttk_mod.LabelFrame(wrapper, text="Paths", padding=10)
            paths.pack(fill="x", padx=0, pady=(0, 8))

            self._add_path_row(ttk_mod, paths, 0, "Notebook Root", self.input_var, self._pick_input)
            self._add_path_row(ttk_mod, paths, 1, "Output Folder", self.output_var, self._pick_output)
            self._add_path_row(ttk_mod, paths, 2, "kfx Plugin Dir", self.plugin_var, self._pick_plugin)
            self._add_path_row(ttk_mod, paths, 3, "MTP Cache Dir", self.mtp_cache_var, self._pick_mtp_cache)

            for col in (1, 2):
                paths.columnconfigure(col, weight=1)

            controls = ttk_mod.Frame(wrapper)
            controls.pack(fill="x", pady=(0, 8))

            ttk_mod.Button(controls, text="Connect Kindle", command=self._connect_kindle).pack(side="left")
            ttk_mod.Button(controls, text="Scan Notebooks", command=self.scan_notebooks).pack(side="left", padx=(8, 0))
            ttk_mod.Button(controls, text="Convert", command=self.convert_clicked).pack(side="left", padx=(8, 0))

            ttk_mod.Label(controls, text="Device:").pack(side="left", padx=(16, 4))
            ttk_mod.Entry(controls, textvariable=self.device_name_var, width=18).pack(side="left")

            ttk_mod.Checkbutton(
                controls,
                text="Use Clean Title (if available)",
                variable=self.use_title_var,
            ).pack(side="left", padx=(16, 0))

            ttk_mod.Checkbutton(
                controls,
                text="Skip Existing PDFs",
                variable=self.skip_existing_var,
            ).pack(side="left", padx=(10, 0))

            ttk_mod.Checkbutton(
                controls,
                text="Only Selected",
                variable=self.only_selected_var,
            ).pack(side="left", padx=(10, 0))

            list_frame = ttk_mod.LabelFrame(wrapper, text="Notebooks", padding=8)
            list_frame.pack(fill="both", expand=True)

            columns = ("folder", "pdf", "nbk")
            self.tree = ttk_mod.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
            self.tree.heading("folder", text="Folder")
            self.tree.heading("pdf", text="PDF Name Preview")
            self.tree.heading("nbk", text="NBK Path")
            self.tree.column("folder", width=290, stretch=False)
            self.tree.column("pdf", width=240, stretch=False)
            self.tree.column("nbk", width=560, stretch=True)

            y_scroll = ttk_mod.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=y_scroll.set)
            self.tree.pack(side="left", fill="both", expand=True)
            y_scroll.pack(side="right", fill="y")

            status = ttk_mod.Frame(wrapper)
            status.pack(fill="x", pady=(8, 0))

            self.progress = ttk_mod.Progressbar(status, mode="determinate", maximum=100, value=0)
            self.progress.pack(fill="x")

            self.status_label = ttk_mod.Label(status, text="Ready")
            self.status_label.pack(anchor="w", pady=(4, 0))

            logs = ttk_mod.LabelFrame(wrapper, text="Activity Log", padding=8)
            logs.pack(fill="both", expand=False, pady=(8, 0))

            self.log_text = tk.Text(logs, height=10, wrap="word")
            log_scroll = ttk_mod.Scrollbar(logs, orient="vertical", command=self.log_text.yview)
            self.log_text.configure(yscrollcommand=log_scroll.set)
            self.log_text.pack(side="left", fill="both", expand=True)
            log_scroll.pack(side="right", fill="y")

        def _add_path_row(self, ttk_mod, parent, row, label, var, browse_cmd):
            ttk_mod.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            entry = ttk_mod.Entry(parent, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            ttk_mod.Button(parent, text="Browse", command=browse_cmd).grid(row=row, column=2, padx=(8, 0), pady=4)

        def _set_status(self, text: str) -> None:
            self.status_label.config(text=text)

        def _log(self, text: str) -> None:
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{ts}] {text}\n")
            self.log_text.see("end")

        def _pick_input(self):
            path = filedialog.askdirectory(title="Select notebook root directory")
            if path:
                self.input_var.set(path)

        def _pick_output(self):
            path = filedialog.askdirectory(title="Select output directory")
            if path:
                self.output_var.set(path)

        def _pick_plugin(self):
            path = filedialog.askdirectory(title="Select directory containing kfxlib")
            if path:
                self.plugin_var.set(path)

        def _pick_mtp_cache(self):
            path = filedialog.askdirectory(title="Select local cache folder for MTP notebook sync")
            if path:
                self.mtp_cache_var.set(path)

        def _connect_kindle(self):
            self._set_status("Connecting Kindle...")
            self.progress.config(mode="indeterminate")
            self.progress.start(10)

            def worker():
                try:
                    detected = detect_kindle_notebook_root()
                    if detected:
                        self.events.put(("kindle_ok", (detected, 0, "drive")))
                        return

                    device_name = self.device_name_var.get().strip() or "Kindle Scribe"
                    cache_root = self.mtp_cache_var.get().strip()
                    if not cache_root:
                        raise RuntimeError("Please configure an MTP cache directory")

                    local_root, copied = sync_kindle_notebooks_via_mtp(device_name, cache_root)
                    self.events.put(("kindle_ok", (local_root, copied, "mtp")))
                except Exception as exc:
                    self.events.put(("kindle_err", str(exc)))

            threading.Thread(target=worker, daemon=True).start()

        def scan_notebooks(self):
            root_dir = self.input_var.get().strip()
            plugin_dir = self.plugin_var.get().strip()

            if not os.path.isdir(root_dir):
                messagebox.showerror("Invalid path", "Notebook root directory does not exist.")
                return

            self._set_status("Scanning notebooks...")
            self.progress.config(mode="indeterminate")
            self.progress.start(10)

            def worker():
                try:
                    entries = find_all_nbk_dirs(root_dir)
                    rows: list[tuple[str, str, str, str]] = []
                    for nbk_file, _default_pdf, dir_name in entries:
                        if self.use_title_var.get():
                            stem = extract_nbk_title(nbk_file, plugin_dir, dir_name)
                        else:
                            stem = dir_name
                        rows.append((dir_name, stem + ".pdf", nbk_file, dir_name))
                    self.events.put(("scan_ok", rows))
                except Exception as exc:
                    self.events.put(("scan_err", str(exc)))

            threading.Thread(target=worker, daemon=True).start()

        def convert_clicked(self):
            if not self.notebooks:
                messagebox.showwarning("No notebooks", "Please scan notebooks first.")
                return

            plugin_dir = self.plugin_var.get().strip()
            output_dir = self.output_var.get().strip() or None
            skip_existing = self.skip_existing_var.get()
            use_title = self.use_title_var.get()

            selected_iids = set(self.tree.selection()) if self.only_selected_var.get() else set()
            targets = []
            for idx, row in enumerate(self.notebooks):
                iid = str(idx)
                if selected_iids and iid not in selected_iids:
                    continue
                targets.append(row)

            if not targets:
                messagebox.showwarning("No selection", "No notebooks selected for conversion.")
                return

            if output_dir and not os.path.isdir(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as exc:
                    messagebox.showerror("Output folder error", str(exc))
                    return

            self._set_status(f"Converting {len(targets)} notebook(s)...")
            self.progress.config(mode="determinate", maximum=len(targets), value=0)

            def worker():
                ok_count = 0
                skip_count = 0
                fail_count = 0

                for idx, (folder_name, _pdf_preview, nbk_file, dir_name) in enumerate(targets, start=1):
                    try:
                        if use_title:
                            stem = extract_nbk_title(nbk_file, plugin_dir, dir_name)
                        else:
                            stem = folder_name

                        base_dir = output_dir if output_dir else os.path.dirname(nbk_file)
                        pdf_path = os.path.join(base_dir, stem + ".pdf")

                        if skip_existing and os.path.exists(pdf_path):
                            skip_count += 1
                            self.events.put(("log", f"SKIP {pdf_path}"))
                        else:
                            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                            stats = convert(nbk_file, pdf_path, plugin_dir)
                            ok_count += 1
                            self.events.put((
                                "log",
                                f"OK   {pdf_path} ({stats['n_pages']} pages, {stats['n_strokes']} strokes)",
                            ))
                    except Exception as exc:
                        fail_count += 1
                        self.events.put(("log", f"FAIL {nbk_file}: {exc}"))

                    self.events.put(("progress", idx))

                self.events.put(("done", (ok_count, skip_count, fail_count, len(targets))))

            threading.Thread(target=worker, daemon=True).start()

        def _drain_events(self):
            try:
                while True:
                    event, payload = self.events.get_nowait()

                    if event == "scan_ok":
                        rows = payload
                        self.notebooks = rows
                        for item in self.tree.get_children():
                            self.tree.delete(item)
                        for idx, (folder, pdf_preview, nbk_file, _dir_name) in enumerate(rows):
                            self.tree.insert("", "end", iid=str(idx), values=(folder, pdf_preview, nbk_file))
                        self.progress.stop()
                        self.progress.config(mode="determinate", maximum=100, value=0)
                        self._set_status(f"Scan complete: {len(rows)} notebook(s)")
                        self._log(f"Scan complete: {len(rows)} notebook(s) found")

                    elif event == "kindle_ok":
                        local_root, copied, mode = payload
                        self.progress.stop()
                        self.progress.config(mode="determinate", maximum=100, value=0)
                        self.input_var.set(local_root)
                        if not self.output_var.get().strip():
                            self.output_var.set(local_root)

                        if mode == "mtp":
                            self._set_status("Kindle connected via MTP")
                            self._log(f"Kindle MTP sync complete: {copied} file(s) copied to {local_root}")
                        else:
                            self._set_status("Kindle connected via drive path")
                            self._log(f"Kindle notebooks detected at {local_root}")

                    elif event == "kindle_err":
                        self.progress.stop()
                        self.progress.config(mode="determinate", maximum=100, value=0)
                        self._set_status("Kindle connect failed")
                        messagebox.showerror("Kindle connect error", str(payload))

                    elif event == "scan_err":
                        self.progress.stop()
                        self.progress.config(mode="determinate", maximum=100, value=0)
                        self._set_status("Scan failed")
                        messagebox.showerror("Scan error", str(payload))

                    elif event == "log":
                        self._log(str(payload))

                    elif event == "progress":
                        self.progress["value"] = int(payload)

                    elif event == "done":
                        ok_count, skip_count, fail_count, total = payload
                        summary = (
                            f"Finished: {ok_count} converted, {skip_count} skipped, {fail_count} failed, total {total}"
                        )
                        self._set_status(summary)
                        self._log(summary)

            except queue.Empty:
                pass
            finally:
                self.root.after(120, self._drain_events)

    root = tk.Tk()
    NotebookApp(root)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(
        description="Konvertiert Kindle-Scribe-NBK-Dateien in PDF"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="NBK-Datei, Notebook-Verzeichnis, oder Wurzelverzeichnis fuer Batch-Konvertierung",
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Ausgabedatei (.pdf) oder Ausgabeverzeichnis bei --batch",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Alle NBK-Notebooks rekursiv unter <input> konvertieren",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bereits vorhandene PDFs ueberspringen",
    )
    parser.add_argument(
        "--use-title",
        action="store_true",
        help="PDF-Dateinamen aus dem Notebook-Titel ableiten statt UUID-Verzeichnisnamen zu verwenden",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur anzeigen, was konvertiert wuerde",
    )
    parser.add_argument(
        "--plugin-dir",
        default=os.environ.get(
            "KFX_PLUGIN_DIR",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "kfx_plugin"),
        ),
        help="Pfad zum extrahierten kfxlib-Verzeichnis",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Desktop-UI starten (Pfadauswahl, Notebook-Liste, Button-Steuerung)",
    )
    args = parser.parse_args()

    if args.gui:
        run_gui(initial_input=args.input, initial_plugin_dir=args.plugin_dir)
        return

    if not args.input:
        parser.error("input is required unless --gui is used")

    if args.batch:
        batch_convert(
            root=args.input,
            plugin_dir=args.plugin_dir,
            output_dir=args.output,
            skip_existing=args.skip_existing,
            dry_run=args.dry_run,
            use_title=args.use_title,
        )
        return

    # Einzelkonvertierung
    try:
        inp, default_base = resolve_nbk_input(args.input)
    except FileNotFoundError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        sys.exit(1)

    outp = args.output if args.output else default_base + ".pdf"

    if args.dry_run:
        print(f"[DRY] {inp}  ->  {outp}")
        return

    stats = convert(inp, outp, args.plugin_dir)
    print(f"OK: {stats['n_pages']} Seite(n), {stats['n_strokes']} Strokes -> {outp}")
    print(f"Strokes pro Seite: {stats['page_strokes']}")


if __name__ == "__main__":
    main()
