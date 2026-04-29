# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release

### Changed
- Improved stroke rendering quality
- Enhanced GUI responsiveness

### Fixed
- Fixed stroke decoding edge cases

### Security
- None currently

## [1.0.0] - 2026-04-29

### Added
- Core NBK to PDF conversion functionality
- Desktop GUI with notebook preview
- Batch conversion support
- Kindle MTP sync integration (Windows)
- Vector-based stroke rendering with color support
- Highlighter transparency support
- Background guide lines
- Clean title extraction from notebook metadata
- Command-line interface with multiple options
- Comprehensive documentation
- Example notebooks

### Features
- Full support for Kindle Scribe notebooks
- Preserves pen colors (ballpoint, marker, highlighter)
- Scalable vector output
- Progress tracking for batch operations
- Skip existing PDFs option
- Custom output directory support

---

## Version History Notes

### Versioning Scheme

We use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes or major feature releases
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes and minor improvements

### Release Process

1. Update version in `setup.py` and `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag -a v1.0.0 -m "Release 1.0.0"`
4. Push tag: `git push origin v1.0.0`
5. GitHub Actions creates release

---

[Unreleased]: https://github.com/yourusername/downloader/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/downloader/releases/tag/v1.0.0
