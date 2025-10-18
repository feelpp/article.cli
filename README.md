# Article CLI

[![CI](https://github.com/feelpp/article.cli/actions/workflows/ci.yml/badge.svg)](https://github.com/feelpp/article.cli/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/article-cli.svg)](https://badge.fury.io/py/article-cli)
[![Python Support](https://img.shields.io/pypi/pyversions/article-cli.svg)](https://pypi.org/project/article-cli/)

A command-line tool for managing LaTeX articles with git integration and Zotero bibliography synchronization.

## Features

- **Repository Initialization**: Complete setup for LaTeX article projects with one command
- **LaTeX Compilation**: Compile documents with latexmk/pdflatex, watch mode, shell escape support
- **GitHub Actions Workflows**: Automated PDF compilation, artifact upload, and GitHub releases
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
```

## Usage

### Repository Initialization

```bash
# Initialize a new article repository (auto-detects main .tex file)
article-cli init --title "My Article Title" --authors "John Doe,Jane Smith"

# Specify custom Zotero group ID
article-cli init --title "My Article" --authors "Author" --group-id 1234567

# Specify main .tex file explicitly
article-cli init --title "My Article" --authors "Author" --tex-file article.tex

# Force overwrite existing files
article-cli init --title "My Article" --authors "Author" --force
```

The `init` command sets up:
- **GitHub Actions workflow** for automated PDF compilation and releases
- **pyproject.toml** with dependencies and article-cli configuration
- **README.md** with comprehensive documentation
- **.gitignore** with LaTeX-specific patterns
- **VS Code configuration** for LaTeX Workshop with auto-build and SyncTeX

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

# Enable shell escape (for code highlighting, etc.)
article-cli compile --shell-escape

# Watch for changes and auto-recompile
article-cli compile --watch

# Clean before and after compilation
article-cli compile --clean-first --clean-after

# Specify output directory
article-cli compile --output-dir build/
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

### v1.0.0
- Initial release
- Git release management
- Zotero bibliography synchronization
- LaTeX build file cleanup
- Configuration file support