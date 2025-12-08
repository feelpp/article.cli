# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.1] - 2025-12-08

### Fixed
- **Font download fixes**: Switch from `urllib` to `requests` library for better redirect handling
- **Roboto Mono URL**: Updated to GitHub archive (Google Fonts URL was returning HTML instead of zip)
- **Added Roboto font**: Include Google's sans-serif font family as default
- **Marianne font**: Moved to optional sources due to Cloudflare protection on French government website

## [1.3.0] - 2025-12-08

### Added
- **New `install-theme` command**: Download and install Beamer themes for presentations
  - `article-cli install-theme numpex` - Install numpex theme
  - `article-cli install-theme --list` - List available themes
  - `article-cli install-theme --dir themes/` - Install to custom directory
  - `article-cli install-theme my-theme --url URL` - Install from custom URL
  - Built-in support for numpex theme from presentation.template.d
  - Automatic extraction of .sty files and theme directories (e.g., images/)
  - Configurable via `[themes]` section in config file
  - Detection of font/engine requirements for themes
- New `ThemeInstaller` class for theme management
- New `get_themes_config()` method in Config class
- 31 new tests for theme installation functionality

## [1.2.0] - 2025-11-18

### Added
- Init command now creates main.tex file if no .tex file exists in repository
- Support for initializing completely empty repositories

### Changed
- Init command no longer requires pre-existing .tex file
- Init command respects existing files (won't overwrite without --force flag)
- Improved empty repository handling for better user experience

## [1.1.1] - 2025-10-18

### Fixed
- Code formatting issues for CI compliance
- Remove unused imports in latex_compiler.py and repository_setup.py
- Add proper None check for process.stdout in latex_compiler.py
- Update .flake8 configuration to handle YAML template formatting
- All linting checks now pass (black, flake8, mypy)

## [1.1.0] - 2025-10-18

### Added
- **New `init` command**: Complete repository initialization for LaTeX article projects
  - Creates GitHub Actions workflows for automated PDF compilation and releases
  - Generates pyproject.toml with article-cli configuration
  - Creates README.md with project documentation and usage instructions
  - Sets up .gitignore with LaTeX-specific entries
  - Auto-detects main .tex file or allows manual specification
  - Supports custom Zotero group IDs and multiple authors
- **New `compile` command**: LaTeX document compilation with various engines and options
  - `article-cli compile main.tex` - Compile with latexmk (default)
  - `article-cli compile --engine pdflatex` - Use pdflatex engine
  - `article-cli compile --shell-escape` - Enable shell escape for code highlighting
  - `article-cli compile --watch` - Watch for changes and auto-recompile
  - `article-cli compile --clean-first --clean-after` - Auto-clean build files
  - Auto-detection of main .tex file if not specified
  - Support for custom output directories
  - Real-time output streaming in watch mode
  - Dependency checking for LaTeX tools
- New `RepositorySetup` class for repository scaffolding
- New `LaTeXCompiler` class with engine abstraction
- Comprehensive workflow template based on article.dirac best practices
- Project configuration templates with embedded article-cli settings
- VS Code configuration files in `init` command
  - `.vscode/settings.json` with LaTeX Workshop configuration
  - `.vscode/ltex.dictionary.en-US.txt` with common LaTeX/math terms
  - `.vscode/ltex.hiddenFalsePositives.en-US.txt` for spell checking
- LaTeX configuration options in config files:
  - `engine` - Default compilation engine (latexmk/pdflatex)
  - `shell_escape` - Enable shell escape by default
  - `timeout` - Compilation timeout in seconds

### Changed
- Enhanced CLI help text with init and compile command examples
- Updated documentation to reflect new commands
- Improved repository structure guidance
- Configuration system now supports LaTeX compilation settings
- Config display shows new LaTeX compilation options
- Auto-build on save enabled by default in VS Code
- SyncTeX support configured

### Features
- **One-command setup**: `article-cli init --title "Article Title" --authors "John Doe,Jane Smith"`
- **Automatic detection**: Finds main .tex file automatically
- **Template-based**: Uses proven templates from article.dirac
- **Configurable**: Supports custom group IDs and force overwrite
- **Complete CI/CD**: Includes full GitHub Actions pipeline with:
  - Automated PDF compilation on push/PR
  - GitHub releases on version tags
  - Artifact upload and verification
  - Zotero bibliography integration
- **LaTeX compilation**: Command-line arguments mimic LaTeX Workshop configuration
- **Multi-pass compilation**: Multiple compilation passes for cross-references (pdflatex)
- **Bibliography processing**: Automatic bibliography processing (bibtex/biber)
- **Watch mode**: latexmk continuous preview with real-time output
- **Error handling**: Comprehensive error handling and user feedback

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

[1.3.1]: https://github.com/feelpp/article.cli/releases/tag/v1.3.1
[1.3.0]: https://github.com/feelpp/article.cli/releases/tag/v1.3.0
[1.2.0]: https://github.com/feelpp/article.cli/releases/tag/v1.2.0
[1.1.1]: https://github.com/feelpp/article.cli/releases/tag/v1.1.1
[1.1.0]: https://github.com/feelpp/article.cli/releases/tag/v1.1.0
[1.0.3]: https://github.com/feelpp/article.cli/releases/tag/v1.0.3
[1.0.2]: https://github.com/feelpp/article.cli/releases/tag/v1.0.2
[1.0.1]: https://github.com/feelpp/article.cli/releases/tag/v1.0.1
[1.0.0]: https://github.com/feelpp/article.cli/releases/tag/v1.0.0