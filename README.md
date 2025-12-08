# Article CLI

[![CI](https://github.com/feelpp/article.cli/actions/workflows/ci.yml/badge.svg)](https://github.com/feelpp/article.cli/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/article-cli.svg)](https://badge.fury.io/py/article-cli)
[![Python Support](https://img.shields.io/pypi/pyversions/article-cli.svg)](https://pypi.org/project/article-cli/)

A command-line tool for managing LaTeX articles and presentations with git integration and Zotero bibliography synchronization.

## Features

- **Repository Initialization**: Complete setup for LaTeX article or presentation projects with one command
- **Project Types**: Support for articles, Beamer presentations, and posters
- **LaTeX Compilation**: Compile documents with latexmk/pdflatex/xelatex/lualatex, watch mode, shell escape support
- **Font Installation**: Download and install fonts for XeLaTeX projects (Marianne, Roboto Mono, etc.)
- **GitHub Actions Workflows**: Automated PDF compilation with XeLaTeX support, artifact upload, and GitHub releases
- **Git Release Management**: Create, list, and delete releases with gitinfo2 support
- **Zotero Integration**: Synchronize bibliography from Zotero with robust pagination and error handling
- **LaTeX Build Management**: Clean build files and manage LaTeX compilation artifacts
- **Git Hooks Setup**: Automated setup of git hooks for gitinfo2 integration
- **Project Configuration**: Auto-generates pyproject.toml with article-cli settings
- **Documentation**: Creates README with build instructions and usage guide

## Installation

### From PyPI (recommended)

```bash
pip install article-cli
```

### From Source

```bash
git clone https://github.com/feelpp/article.cli.git
cd article.cli
pip install -e .
```

## Quick Start

### For New Projects

1. **Initialize your LaTeX article repository**:
   ```bash
   cd your-article-repo
   article-cli init --title "Your Article Title" --authors "Author One,Author Two"
   ```

   This creates:
   - `.github/workflows/latex.yml` - Complete CI/CD pipeline
   - `pyproject.toml` - Project configuration with article-cli settings
   - `README.md` - Documentation and usage instructions
   - `.gitignore` - LaTeX-specific ignore rules
   - `.vscode/settings.json` - LaTeX Workshop configuration
   - `.vscode/ltex.dictionary.en-US.txt` - Custom dictionary

2. **Configure Zotero** (add as GitHub secret):
   ```bash
   export ZOTERO_API_KEY="your_api_key_here"
   ```

3. **Setup git hooks and update bibliography**:
   ```bash
   article-cli setup
   article-cli update-bibtex
   ```

4. **Commit and push** to trigger automated PDF compilation!

### For Existing Projects

1. **Setup git hooks** (run once per repository):
   ```bash
   article-cli setup
   ```

2. **Configure Zotero credentials**:
   ```bash
   export ZOTERO_API_KEY="your_api_key_here"
   export ZOTERO_GROUP_ID="your_group_id"  # or ZOTERO_USER_ID
   ```

3. **Update bibliography from Zotero**:
   ```bash
   article-cli update-bibtex
   ```

4. **Create a release**:
   ```bash
   article-cli create v1.0.0
   ```

## Configuration

### Environment Variables

- `ZOTERO_API_KEY`: Your Zotero API key (required for bibliography updates)
- `ZOTERO_USER_ID`: Your Zotero user ID (alternative to group ID)
- `ZOTERO_GROUP_ID`: Your Zotero group ID (alternative to user ID)

### Local Configuration File

Create a `.article-cli.toml` file in your project root for project-specific settings:

```toml
[zotero]
api_key = "your_api_key_here"
group_id = "4678293"  # Default for article.template
# user_id = "your_user_id"  # alternative to group_id
output_file = "references.bib"

[git]
auto_push = true
default_branch = "main"

[latex]
clean_extensions = [".aux", ".bbl", ".blg", ".log", ".out", ".synctex.gz"]

[fonts]
directory = "fonts"

[fonts.sources]
marianne = "https://github.com/ArnaudBelcworking/Marianne/archive/refs/heads/master.zip"
roboto-mono = "https://github.com/googlefonts/RobotoMono/releases/download/v3.000/RobotoMono-v3.000.zip"

[themes]
directory = "."

# Custom theme sources (numpex is built-in)
# [themes.sources.my-theme]
# url = "https://example.com/theme.zip"
# description = "My custom theme"
# files = ["beamerthememytheme.sty"]
# requires_fonts = false
# engine = "pdflatex"
```

## Usage

### Repository Initialization

```bash
# Initialize a new article repository (auto-detects main .tex file)
article-cli init --title "My Article Title" --authors "John Doe,Jane Smith"

# Initialize a Beamer presentation project
article-cli init --title "My Presentation" --authors "Author" --type presentation

# Initialize with numpex theme (requires theme files from presentation.template.d)
article-cli init --title "NumPEx Talk" --authors "Author" --type presentation --theme numpex

# Specify custom Zotero group ID
article-cli init --title "My Article" --authors "Author" --group-id 1234567

# Specify main .tex file explicitly
article-cli init --title "My Article" --authors "Author" --tex-file article.tex

# Force overwrite existing files
article-cli init --title "My Article" --authors "Author" --force
```

The `init` command sets up:
- **GitHub Actions workflow** for automated PDF compilation and releases (with XeLaTeX support for presentations)
- **pyproject.toml** with dependencies and article-cli configuration
- **README.md** with comprehensive documentation
- **.gitignore** with LaTeX-specific patterns
- **VS Code configuration** for LaTeX Workshop with auto-build and SyncTeX
- **Font configuration** (for presentation projects using custom themes)

### Git Release Management

```bash
# Create a new release
article-cli create v1.2.3

# List recent releases
article-cli list --count 10

# Delete a release
article-cli delete v1.2.3
```

### Bibliography Management

```bash
# Update bibliography from Zotero
article-cli update-bibtex

# Specify custom output file
article-cli update-bibtex --output my-refs.bib

# Skip backup creation
article-cli update-bibtex --no-backup
```

### LaTeX Compilation

```bash
# Compile with latexmk (default engine)
article-cli compile

# Compile specific file with latexmk
article-cli compile main.tex

# Compile with pdflatex engine
article-cli compile --engine pdflatex

# Compile with XeLaTeX (for custom fonts)
article-cli compile --engine xelatex

# Compile with LuaLaTeX
article-cli compile --engine lualatex

# Enable shell escape (for code highlighting, etc.)
article-cli compile --shell-escape

# Watch for changes and auto-recompile
article-cli compile --watch

# Clean before and after compilation
article-cli compile --clean-first --clean-after

# Specify output directory
article-cli compile --output-dir build/
```

### Font Installation

Install fonts for XeLaTeX projects (useful for custom Beamer themes):

```bash
# Install default fonts (Marianne, Roboto Mono) to fonts/ directory
article-cli install-fonts

# Install to a custom directory
article-cli install-fonts --dir custom-fonts/

# Force re-download even if fonts exist
article-cli install-fonts --force

# List installed fonts
article-cli install-fonts --list
```

**Default fonts:**
- **Marianne**: French government official font
- **Roboto Mono**: Google's monospace font for code

### Theme Installation

Install Beamer themes for presentations:

```bash
# List available themes
article-cli install-theme --list

# Install numpex theme (NumPEx Beamer theme)
article-cli install-theme numpex

# Install to a custom directory
article-cli install-theme numpex --dir themes/

# Force re-download even if theme exists
article-cli install-theme numpex --force

# Install from a custom URL
article-cli install-theme my-theme --url https://example.com/theme.zip
```

**Available themes:**
- **numpex**: NumPEx Beamer theme following French government visual identity (requires XeLaTeX and custom fonts)

**Complete presentation setup:**
```bash
# 1. Install the theme
article-cli install-theme numpex

# 2. Install required fonts
article-cli install-fonts

# 3. Compile with XeLaTeX
article-cli compile presentation.tex --engine xelatex
```

### Project Setup

```bash
# Setup git hooks for gitinfo2
article-cli setup

# Clean LaTeX build files
article-cli clean
```

### Advanced Usage

```bash
# Override configuration via command line
article-cli update-bibtex --api-key YOUR_KEY --group-id YOUR_GROUP

# Specify custom configuration file
article-cli --config custom-config.toml update-bibtex
```

## Version Format

Release versions must follow the semantic versioning format:
- `vX.Y.Z` for stable releases (e.g., `v1.2.3`)
- `vX.Y.Z-pre.N` for pre-releases (e.g., `v1.2.3-pre.1`)

## Requirements

- Python 3.8+
- Git repository with gitinfo2 package (for LaTeX integration)
- Zotero account with API access (for bibliography features)

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Changelog

### v1.2.0
- Add font installation command (`install-fonts`) for XeLaTeX projects
- Support Marianne and Roboto Mono fonts by default
- Add theme installation command (`install-theme`) for Beamer presentations
- Built-in support for numpex theme with automatic download
- Extended GitHub Actions workflow with XeLaTeX and multi-document support
- Add presentation project type with Beamer template support
- Add `--engine` option for xelatex and lualatex compilation
- Improved CI/CD with font installation steps

### v1.1.0
- Add `init` command for repository initialization
- Add `compile` command with watch mode and multiple engines
- GitHub Actions workflow generation
- VS Code configuration generation

### v1.0.0
- Initial release
- Git release management
- Zotero bibliography synchronization
- LaTeX build file cleanup
- Configuration file support