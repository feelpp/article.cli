# AI Agents Guide for Article CLI

This document provides guidance for AI agents working on the article-cli package, including common tasks, version management, and maintenance procedures.

## 🚀 Version Bump Process

When releasing a new version, **ALL** of these files must be updated with the new version number:

### Required Files to Update:

1. **`pyproject.toml`** - Line ~7
   ```toml
   version = "1.0.X"
   ```

2. **`src/article_cli/__init__.py`** - Line ~11
   ```python
   __version__ = "1.0.X"
   ```

3. **`CHANGELOG.md`** - Add new version section at top
   ```markdown
   ## [1.0.X] - YYYY-MM-DD
   ### Added/Fixed/Changed
   - Description of changes
   ```

4. **`CHANGELOG.md`** - Update links section at bottom
   ```markdown
   [1.0.X]: https://github.com/feelpp/article.cli/releases/tag/v1.0.X
   ```

### Version Bump Checklist:

- [ ] Update `pyproject.toml` version
- [ ] Update `src/article_cli/__init__.py` __version__
- [ ] Add new section to `CHANGELOG.md`
- [ ] Update CHANGELOG.md links
- [ ] Commit changes: `git commit -m "chore: bump version to 1.0.X"`
- [ ] Push changes: `git push`
- [ ] Create and push git tag: `git tag v1.0.X -m "Release v1.0.X" && git push origin v1.0.X`
- [ ] **Create GitHub release**: `gh release create v1.0.X --title "Release v1.0.X" --notes "Release notes here"`
  - ⚠️ **IMPORTANT**: The PyPI publishing workflow is triggered by GitHub releases, NOT by git tags
  - The workflow listens for `release: types: [published]` events
- [ ] Verify PyPI publication via trusted publishing at https://github.com/feelpp/article.cli/actions

### Semantic Versioning Guide:

- **MAJOR (2.0.0)**: Breaking changes to CLI interface or API
- **MINOR (1.1.0)**: New features, backwards compatible
- **PATCH (1.0.1)**: Bug fixes, backwards compatible

## 🧪 Testing Before Release

Always run these checks before releasing:

```bash
# Code quality checks
black --check src/
flake8 src/
mypy src/

# Local functionality test
uv pip install -e .
article-cli --version
article-cli --help
article-cli config show
```

## 📁 Project Structure

```
article.cli/
├── .github/workflows/          # CI/CD automation
│   ├── ci.yml                 # Build, test, lint pipeline
│   └── publish.yml            # PyPI publishing (trusted)
├── src/article_cli/           # Python package source
│   ├── __init__.py           # Package version & exports
│   ├── cli.py                # Main CLI interface
│   ├── config.py             # Configuration management
│   ├── zotero.py             # Zotero API integration
│   └── git_manager.py        # Git operations
├── tests/                     # Test suite
├── pyproject.toml            # Package configuration
├── CHANGELOG.md              # Release history
├── README.md                 # User documentation
├── DEVELOPMENT.md            # Developer guide
├── MIGRATION.md              # Migration from old scripts
├── PYPI_SETUP.md            # PyPI publishing setup
└── AGENTS.md                # This file
```

## 🔧 Common Maintenance Tasks

### Adding New Commands

1. Add command parser in `src/article_cli/cli.py`
2. Implement command handler function
3. Add to `create_parser()` subcommands
4. Update help text and documentation
5. Add tests for new functionality

### Updating Dependencies

1. Update `pyproject.toml` dependencies section
2. Test with different Python versions (3.8-3.12)
3. Update CI if needed
4. Document any breaking changes

### Configuration Changes

1. Update `src/article_cli/config.py` for new settings
2. Update sample config generation
3. Update documentation examples
4. Maintain backward compatibility

## 🏗️ CI/CD Pipeline

### Automated Workflows:

1. **Build and Test** (`ci.yml`):
   - Triggered on: push to main/develop, pull requests
   - Tests: Python 3.8, 3.9, 3.10, 3.11, 3.12
   - Checks: Black, flake8, mypy, CLI functionality
   - Artifacts: Built package for distribution

2. **Publish to PyPI** (`publish.yml`):
   - Triggered on: GitHub release published
   - Uses: Trusted publishing (no tokens required)
   - Publishes to: https://pypi.org/project/article-cli/

### Manual Release Process:

```bash
# 1. Prepare release
git checkout main
git pull origin main

# 2. Bump version (update all files listed above)
# 3. Commit and push
git add -A
git commit -m "chore: bump version to 1.0.X"
git push

# 4. Create GitHub release (triggers PyPI publishing)
gh release create v1.0.X --title "v1.0.X - Description" --notes "Release notes"
```

## 🔍 Troubleshooting

### Common Issues:

1. **PyPI Publishing Fails**:
   - Check trusted publishing configuration on PyPI
   - Verify GitHub repository settings
   - Ensure version number is incremented

2. **Version Mismatch**:
   - Ensure `pyproject.toml` and `__init__.py` versions match
   - Reinstall package locally: `pip install -e .`
   - Test: `article-cli --version`

3. **CI Failures**:
   - Check code formatting: `black src/`
   - Check linting: `flake8 src/`
   - Check types: `mypy src/`
   - Update GitHub Actions if deprecated

### Environment Setup:

```bash
# Fresh development environment with uv
cd /Users/prudhomm/Devel/Articles/article.cli
uv venv
source .venv/bin/activate
uv pip install -e .
uv pip install black flake8 mypy types-requests pytest
```

## 📚 Documentation Locations

- **User Guide**: `README.md`
- **Development**: `DEVELOPMENT.md`
- **Migration**: `MIGRATION.md`
- **PyPI Setup**: `PYPI_SETUP.md`
- **Release History**: `CHANGELOG.md`
- **This Guide**: `AGENTS.md`

## 🎯 Default Configuration Values

- **Default Zotero Group ID**: `4678293` (for article.template)
- **Default Output File**: `references.bib`
- **Default Branch**: `main`
- **Python Support**: 3.8 - 3.12

## 🔗 Important Links

- **GitHub Repository**: https://github.com/feelpp/article.cli
- **PyPI Package**: https://pypi.org/project/article-cli/
- **CI/CD Actions**: https://github.com/feelpp/article.cli/actions
- **PyPI Trusted Publishing**: https://pypi.org/manage/project/article-cli/settings/publishing/

## 🐛 Troubleshooting

### PyPI Publishing Not Triggered

**Issue**: Pushed git tag but PyPI publishing workflow didn't run.

**Cause**: The workflow is triggered by `release: types: [published]`, not by git tag pushes.

**Solution**:
```bash
# After pushing your tag:
git tag v1.0.X -m "Release v1.0.X"
git push origin v1.0.X

# Create the GitHub release (this triggers PyPI publishing):
gh release create v1.0.X --title "Release v1.0.X" --notes "Release notes"
```

**Verification**: Check workflow runs at https://github.com/feelpp/article.cli/actions

### Version Sync Issues

**Issue**: PyPI and package versions don't match.

**Cause**: Forgot to update one of the version files.

**Solution**: Always update BOTH files:
- `pyproject.toml` - Line with `version = "1.0.X"`
- `src/article_cli/__init__.py` - Line with `__version__ = "1.0.X"`

**Verify locally**:
```bash
uv pip install -e .
article-cli --version
```

---

**Remember**: Always test locally before releasing, and ensure all version-related files are updated consistently!