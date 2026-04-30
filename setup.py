"""
Setup script for Kindle Scribe Notebook PDF Converter.

Installs all PyPI dependencies and automatically downloads the KFX Input
plugin from GitHub (kluyg/calibre-kfx-input), extracting only the kfxlib
package into kfx_plugin/kfxlib/, then registers it on sys.path via a .pth file.
"""

import io
import re
import site
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop

RUNTIME_DEPENDENCIES = [
    "reportlab>=4.0.0",
    "pypdf>=3.0.0",
    "lxml>=4.9.0",
    "Pillow>=9.0.0",
    "beautifulsoup4>=4.12.0",
]

# GitHub mirror of the KFX Input plugin (contains kfxlib/ at the repo root)
_KFX_REPO = "https://github.com/kluyg/calibre-kfx-input"
_KFX_ZIP_URL = f"{_KFX_REPO}/archive/refs/heads/main.zip"


def _download_and_install_kfxlib(plugin_dir: Path) -> bool:
    """
    Download the KFX Input plugin ZIP from GitHub and extract just the
    kfxlib package into plugin_dir/kfxlib/. Returns True on success.
    """
    print(f"Downloading KFX Input plugin from:\n  {_KFX_ZIP_URL}")
    try:
        with urllib.request.urlopen(_KFX_ZIP_URL, timeout=60) as resp:
            zip_data = resp.read()
    except Exception as exc:
        print(f"  Download failed: {exc}")
        return False

    plugin_dir.mkdir(parents=True, exist_ok=True)
    kfxlib_dest = plugin_dir / "kfxlib"

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # GitHub zips have a top-level "calibre-kfx-input-main/" prefix
        kfxlib_entries = [
            name for name in zf.namelist()
            if re.search(r"(^|/)kfxlib/", name)
        ]
        if not kfxlib_entries:
            print("  kfxlib not found inside the downloaded ZIP.")
            return False

        sample = kfxlib_entries[0]
        prefix = sample[: sample.index("kfxlib/")]

        for entry in zf.namelist():
            if not entry.startswith(prefix + "kfxlib/"):
                continue
            rel = entry[len(prefix):]       # strip repo root prefix
            dest = plugin_dir / rel
            if entry.endswith("/"):
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(entry))

    if kfxlib_dest.is_dir():
        print(f"  kfxlib extracted to {kfxlib_dest}")
        return True

    print("  Extraction did not produce a kfxlib directory.")
    return False


def _install_pypi_deps():
    """Install runtime dependencies needed for PDF generation and kfxlib."""
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", *RUNTIME_DEPENDENCIES]
    )


def _register_kfxlib():
    """
    Ensure kfx_plugin/kfxlib exists (downloading it if necessary), then
    register kfx_plugin/ on sys.path via a .pth file in site-packages.
    """
    root = Path(__file__).parent.resolve()
    plugin_dir = root / "kfx_plugin"
    kfxlib_dir = plugin_dir / "kfxlib"

    if not kfxlib_dir.is_dir():
        print("\nkfxlib not found locally — attempting automatic download…")
        if not _download_and_install_kfxlib(plugin_dir):
            print(
                "\n*** Automatic download failed — manual step required ***\n"
                "Clone or download the plugin from:\n"
                f"  {_KFX_REPO}\n"
                "Then copy the 'kfxlib' folder to:\n"
                f"  {kfxlib_dir}\n"
                "and re-run:  python setup.py\n"
            )
            return

    # Write a .pth file so `import kfxlib` works in this environment
    site_pkgs = site.getsitepackages()
    pth_path = Path(site_pkgs[0]) / "kindle_kfxlib.pth"
    pth_path.write_text(str(plugin_dir) + "\n", encoding="utf-8")
    print(f"kfxlib registered via {pth_path}")


class CustomInstall(install):
    def run(self):
        _install_pypi_deps()
        super().run()
        _register_kfxlib()


class CustomDevelop(develop):
    def run(self):
        _install_pypi_deps()
        super().run()
        _register_kfxlib()


if __name__ == "__main__" and len(sys.argv) == 1:
    # Running as `py setup.py` with no subcommand — install everything directly.
    _install_pypi_deps()
    _register_kfxlib()
else:
    setup(
        install_requires=RUNTIME_DEPENDENCIES,
        cmdclass={
            "install": CustomInstall,
            "develop": CustomDevelop,
        }
    )


