# Migration Guide

This guide helps you migrate existing article repositories from local `a.py`/`a.cli` scripts to the centralized `article-cli` package.

## Overview

The `article-cli` package centralizes the maintenance of the article management tools previously distributed as `a.py` or `a.cli` files across multiple repositories.

## Migration Steps

### 1. Update Dependencies

Add `article-cli` to your repository's `pyproject.toml`:

```toml
[project]
dependencies = [
    "article-cli>=1.0.0",
    # ... your other dependencies
]

# Optional: Add tool configuration
[tool.article-cli.zotero]
api_key = "your_api_key"  # Or use environment variable
group_id = "4912261"      # Your Zotero group ID
output_file = "references.bib"

[tool.article-cli.git]
auto_push = true
default_branch = "main"

[tool.article-cli.latex]
clean_extensions = [".aux", ".bbl", ".blg", ".log", ".out", ".synctex.gz"]
```

### 2. Setup Virtual Environment

Create a setup script or update your existing one:

```bash
#!/bin/bash
# setup-dev-env.sh

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "✓ Created virtual environment"
fi

# Activate virtual environment
source venv/bin/activate
echo "✓ Activated virtual environment"

# Install dependencies
pip install -e .
echo "✓ Installed dependencies including article-cli"

# Setup git hooks
article-cli setup
echo "✓ Setup git hooks for gitinfo2"

echo "✅ Development environment ready!"
echo "Run 'source venv/bin/activate' to activate the environment"
```

### 3. Replace Local Scripts

Remove the old `a.py` or `a.cli` files and update any scripts that reference them:

```bash
# Old way
./a.py create v1.0.0
./a.cli update-bibtex

# New way
article-cli create v1.0.0
article-cli update-bibtex
```

### 4. Update Documentation

Update your repository's README to reflect the new setup:

```markdown
## Setup

1. Create and activate virtual environment:
   ```bash
   ./setup-dev-env.sh
   source venv/bin/activate
   ```

2. Configure Zotero credentials:
   ```bash
   export ZOTERO_API_KEY="your_api_key"
   export ZOTERO_GROUP_ID="your_group_id"
   ```

3. Update bibliography:
   ```bash
   article-cli update-bibtex
   ```
```

### 5. Verify Migration

Test the key functionality:

```bash
# Activate environment
source venv/bin/activate

# Test configuration
article-cli config show

# Test Zotero integration (if configured)
article-cli update-bibtex --dry-run

# Test git operations
article-cli list

# Test LaTeX cleanup
article-cli clean
```

## Configuration Migration

### From Environment Variables

If you previously used environment variables, they will continue to work:

```bash
# These still work
export ZOTERO_API_KEY="your_key"
export ZOTERO_GROUP_ID="your_group"
```

### From Local Config Files

If you had custom configuration files, migrate them to the new format:

```toml
# Old .article-cli.toml format (still supported)
[zotero]
api_key = "your_key"
group_id = "your_group"

# New pyproject.toml format (recommended)
[tool.article-cli.zotero]
api_key = "your_key"
group_id = "your_group"
```

## Benefits of Migration

1. **Centralized Maintenance**: Updates to the tool are distributed via PyPI
2. **Version Management**: Semantic versioning ensures compatibility
3. **Professional Packaging**: Proper Python package structure
4. **Enhanced Features**: Group name verification, better error handling
5. **CI/CD Integration**: Automated testing and publishing
6. **Documentation**: Comprehensive docs and examples

## Troubleshooting

### Common Issues

1. **Command not found**: Ensure virtual environment is activated
2. **Import errors**: Run `pip install -e .` to install dependencies  
3. **Permission errors**: Check git hooks permissions after setup
4. **Zotero errors**: Verify API key and group ID configuration

### Getting Help

- Check the [documentation](https://github.com/feelpp/article.cli)
- View configuration: `article-cli config show`
- Open an issue: https://github.com/feelpp/article.cli/issues

## Rollback Plan

If you need to rollback:

1. Keep a backup of your old `a.py`/`a.cli` files
2. Remove `article-cli` from dependencies
3. Restore the old files and scripts
4. Update any calling scripts

However, we recommend migrating forward as the new system provides better maintainability and features.