# Article CLI

A command-line tool for managing LaTeX articles with git integration and Zotero bibliography synchronization.

## Features

- **Git Release Management**: Create, list, and delete releases with gitinfo2 support
- **Zotero Integration**: Synchronize bibliography from Zotero with robust pagination and error handling
- **LaTeX Build Management**: Clean build files and manage LaTeX compilation artifacts
- **Git Hooks Setup**: Automated setup of git hooks for gitinfo2 integration
- **Local Configuration**: Support for project-specific configuration files

## Installation

### From PyPI (recommended)

```bash
pip install article-cli
```

### From Source

```bash
git clone https://github.com/feelpp/article-cli.git
cd article-cli
pip install -e .
```

## Quick Start

1. **Setup git hooks** (run once per repository):
   ```bash
   article-cli setup
   ```

2. **Configure Zotero credentials** (one-time setup):
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
group_id = "6219333"
# user_id = "your_user_id"  # alternative to group_id
output_file = "references.bib"

[git]
auto_push = true
default_branch = "main"

[latex]
clean_extensions = [".aux", ".bbl", ".blg", ".log", ".out", ".synctex.gz"]
```

## Usage

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