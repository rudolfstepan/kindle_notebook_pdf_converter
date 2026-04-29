#!/usr/bin/env python3
"""
Setup script for Kindle Scribe Notebook PDF Converter
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
root_dir = Path(__file__).parent
readme_file = root_dir / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="kindle-notebook-converter",
    version="1.0.0",
    description="Convert Kindle Scribe handwritten notebooks to PDF with vector rendering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/downloader",
    author="Your Name",
    author_email="your.email@example.com",
    license="MIT",
    
    packages=find_packages(where=".", include=["kindle_notebook_pdf_converter*"]),
    
    python_requires=">=3.8",
    
    install_requires=[
        "reportlab>=4.0.0",
        "pypdf>=3.0.0",
        "lxml>=4.9.0",
        "Pillow>=9.0.0",
    ],
    
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "pylint>=2.15.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    
    entry_points={
        "console_scripts": [
            "nbk-convert=kindle_notebook_pdf_converter.nbk_convert:main",
        ],
    },
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business",
        "Topic :: Multimedia",
        "Topic :: Utilities",
    ],
    
    keywords="kindle scribe notebook pdf converter ebook",
    
    project_urls={
        "Documentation": "https://github.com/yourusername/downloader/tree/main/docs",
        "Source": "https://github.com/yourusername/downloader",
        "Tracker": "https://github.com/yourusername/downloader/issues",
    },
    
    include_package_data=True,
    zip_safe=False,
)
