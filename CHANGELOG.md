# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2024-12-19

### Added
- AGENTS.md documentation with comprehensive maintenance guide
- Version bump checklist to prevent version sync issues

### Improved
- Enhanced documentation for AI agent maintenance
- Better project organization with standalone directory structure
## [1.0.2] - 2024-10-10

### Fixed
- Configured PyPI trusted publishing for automated releases
- Resolved trusted publisher configuration for existing package
- Removed duplicate token-based publish workflow

### Infrastructure
- Streamlined CI/CD pipeline with single, secure publish workflow
- Enhanced GitHub Actions with step summaries and modern action versions

## [1.0.1] - 2024-10-10

### Fixed
- Resolved Black code formatting issues across all Python files
- Fixed MyPy type checking errors and import-untyped warnings
- Added proper type stubs (types-requests) to CI workflow
- Enhanced mypy configuration with explicit module overrides
- Fixed PyPI publishing authentication setup

### Changed
- Updated default ZOTERO_GROUP_ID to 4678293 for article.template projects
- Enhanced CI/CD pipeline with better type checking and dependency management
- Added `__main__.py` for python -m article_cli execution support

### Documentation
- Updated README, DEVELOPMENT.md with correct default group ID
- Added comprehensive PyPI setup and migration documentation

## [1.0.0] - 2024-10-10

### Added
- Initial release of article-cli
- Git release management with gitinfo2 support
- Zotero bibliography synchronization with robust pagination and error handling
- LaTeX build file cleanup with configurable extensions
- Git hooks setup for gitinfo2 integration
- Configuration management with TOML support
- Support for both dedicated config files (.article-cli.toml) and pyproject.toml embedding
- Group name verification for Zotero groups
- Environment variable support for all configuration
- Command-line overrides for all settings
- Professional PyPI package structure
- Comprehensive test suite
- Migration scripts for existing repositories
- Development environment setup scripts

### Features
- **Git Operations**: Create, list, and delete releases with automatic gitinfo2 integration
- **Zotero Integration**: Fetch bibliography with rate limiting and pagination support
- **Configuration Priority**: CLI args > env vars > local config > global config > defaults
- **Group Verification**: Shows Zotero group names alongside IDs for verification
- **Flexible Setup**: Works with global installation or per-repository virtual environments
- **Modern Standards**: PEP 518/621 compliant packaging

### Configuration
- Project-specific configuration via pyproject.toml `[tool.article-cli]` section
- Global configuration via `~/.article-cli.toml`
- Environment variable support for all settings
- Command-line override capability

### Commands
- `article-cli setup` - Setup git hooks
- `article-cli clean` - Clean LaTeX build files
- `article-cli create v1.0.0` - Create releases
- `article-cli list` - List releases
- `article-cli delete v1.0.0` - Delete releases
- `article-cli update-bibtex` - Update bibliography from Zotero
- `article-cli config show` - Show current configuration
- `article-cli config create` - Create sample configuration

[1.0.3]: https://github.com/feelpp/article.cli/releases/tag/v1.0.3[1.0.2]: https://github.com/feelpp/article.cli/releases/tag/v1.0.2
[1.0.1]: https://github.com/feelpp/article.cli/releases/tag/v1.0.1
[1.0.0]: https://github.com/feelpp/article.cli/releases/tag/v1.0.0