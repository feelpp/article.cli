"""
Configuration management for article-cli

Supports both environment variables and TOML configuration files.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import argparse

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # fallback for older Python versions
    except ImportError:
        tomllib = None


class Config:
    """Configuration manager for article-cli"""

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager

        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self._config_data: Dict[str, Any] = {}
        self._load_config()

    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in project directory"""
        if self.config_file:
            config_path = Path(self.config_file)
            if config_path.exists():
                return config_path
            else:
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Look for default config files (in priority order)
        search_paths = [
            Path.cwd()
            / ".article-cli.toml",  # Dedicated config file (highest priority)
            Path.cwd() / "pyproject.toml",  # Project config file
            Path.cwd() / "article-cli.toml",  # Alternative dedicated file
            Path.home() / ".config" / "article-cli" / "config.toml",  # XDG config
            Path.home() / ".article-cli.toml",  # User config (lowest priority)
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_config(self) -> None:
        """Load configuration from file if it exists"""
        config_path = self._find_config_file()

        if config_path and tomllib:
            try:
                with open(config_path, "rb") as f:
                    full_config = tomllib.load(f)

                # Handle pyproject.toml vs dedicated config file
                if config_path.name == "pyproject.toml":
                    # Extract article-cli config section from pyproject.toml
                    self._config_data = full_config.get("tool", {}).get(
                        "article-cli", {}
                    )
                    if self._config_data:
                        print(
                            f"Loaded configuration from: {config_path} [tool.article-cli]"
                        )
                    else:
                        # Fallback: look for legacy sections at root level
                        legacy_sections = ["zotero", "git", "latex"]
                        self._config_data = {
                            k: v for k, v in full_config.items() if k in legacy_sections
                        }
                        if self._config_data:
                            print(f"Loaded legacy configuration from: {config_path}")
                else:
                    # Dedicated config file - use as-is
                    self._config_data = full_config
                    print(f"Loaded configuration from: {config_path}")

            except Exception as e:
                print(f"Warning: Could not load config file {config_path}: {e}")
                self._config_data = {}
        elif config_path and not tomllib:
            print(
                "Warning: TOML support not available. Install with: pip install tomli"
            )
            self._config_data = {}
        else:
            self._config_data = {}

    def get(
        self, section: str, key: str, default: Any = None, env_var: Optional[str] = None
    ) -> Any:
        """
        Get configuration value with priority: CLI args > env vars > config file > default

        Args:
            section: Configuration section name
            key: Configuration key name
            default: Default value if not found
            env_var: Environment variable name to check

        Returns:
            Configuration value
        """
        # Check environment variable first
        if env_var and env_var in os.environ:
            return os.environ[env_var]

        # Check config file
        if section in self._config_data and key in self._config_data[section]:
            return self._config_data[section][key]

        return default

    def get_zotero_config(self) -> Dict[str, Optional[str]]:
        """Get Zotero-specific configuration"""
        return {
            "api_key": self.get("zotero", "api_key", env_var="ZOTERO_API_KEY"),
            "user_id": self.get("zotero", "user_id", env_var="ZOTERO_USER_ID"),
            "group_id": self.get("zotero", "group_id", env_var="ZOTERO_GROUP_ID"),
            "output_file": self.get(
                "zotero", "output_file", "references.bib", env_var="BIBTEX_FILE"
            ),
        }

    def get_git_config(self) -> Dict[str, Any]:
        """Get Git-specific configuration"""
        return {
            "auto_push": self.get("git", "auto_push", False),
            "default_branch": self.get("git", "default_branch", "main"),
        }

    def get_latex_config(self) -> Dict[str, Any]:
        """Get LaTeX-specific configuration"""
        default_extensions = [
            ".aux",
            ".bbl",
            ".blg",
            ".log",
            ".out",
            ".pyg",
            ".fls",
            ".synctex.gz",
            ".toc",
            ".fdb_latexmk",
            ".idx",
            ".ilg",
            ".ind",
            ".chl",
            ".lof",
            ".lot",
        ]

        return {
            "clean_extensions": self.get(
                "latex", "clean_extensions", default_extensions
            ),
            "build_dir": self.get("latex", "build_dir", "."),
            "engine": self.get("latex", "engine", "latexmk"),
            "shell_escape": self.get("latex", "shell_escape", False),
            "timeout": self.get("latex", "timeout", 300),
        }

    def validate_zotero_config(
        self, args: argparse.Namespace
    ) -> Dict[str, Optional[str]]:
        """
        Validate and merge Zotero configuration from args and config

        Args:
            args: Parsed command line arguments

        Returns:
            Dict with validated Zotero configuration

        Raises:
            ValueError: If required configuration is missing
        """
        config = self.get_zotero_config()

        # Override with command line arguments
        if hasattr(args, "api_key") and args.api_key:
            config["api_key"] = args.api_key
        if hasattr(args, "user_id") and args.user_id:
            config["user_id"] = args.user_id
        if hasattr(args, "group_id") and args.group_id:
            config["group_id"] = args.group_id
        if hasattr(args, "output") and args.output:
            config["output_file"] = args.output

        # Validate required fields
        if not config["api_key"]:
            raise ValueError(
                "Zotero API key is required. Set via:\n"
                "  - Command line: --api-key YOUR_KEY\n"
                "  - Environment: export ZOTERO_API_KEY=YOUR_KEY\n"
                '  - Config file: [zotero] api_key = "YOUR_KEY"'
            )

        if not config["user_id"] and not config["group_id"]:
            raise ValueError(
                "Either Zotero user ID or group ID is required. Set via:\n"
                "  - Command line: --user-id ID or --group-id ID\n"
                "  - Environment: export ZOTERO_USER_ID=ID or ZOTERO_GROUP_ID=ID\n"
                '  - Config file: [zotero] user_id = "ID" or group_id = "ID"'
            )

        return config

    def create_sample_config(self, path: Optional[Path] = None) -> Path:
        """
        Create a sample configuration file

        Args:
            path: Optional path for config file

        Returns:
            Path to created config file
        """
        if path is None:
            path = Path.cwd() / ".article-cli.toml"

        sample_config = """# Article CLI Configuration File
# Copy this file to your project root as .article-cli.toml

[zotero]
# Your Zotero API key (get from https://www.zotero.org/settings/keys)
api_key = "your_api_key_here"

# Either user_id OR group_id (not both)
# user_id = "your_user_id"
group_id = "4678293"  # Default group ID for article.template

# Output file for bibliography
output_file = "references.bib"

[git]
# Automatically push after creating releases
auto_push = true

# Default branch name
default_branch = "main"

[latex]
# File extensions to clean
clean_extensions = [
    ".aux", ".bbl", ".blg", ".log", ".out", ".pyg",
    ".fls", ".synctex.gz", ".toc", ".fdb_latexmk",
    ".idx", ".ilg", ".ind", ".chl", ".lof", ".lot"
]

# Build directory (relative to project root)
build_dir = "."

# Default LaTeX engine
engine = "latexmk"  # Options: "latexmk", "pdflatex"

# Enable shell escape by default
shell_escape = false

# Compilation timeout in seconds
timeout = 300
"""

        try:
            with open(path, "w") as f:
                f.write(sample_config)
            print(f"Created sample configuration file: {path}")
            return path
        except Exception as e:
            raise RuntimeError(f"Could not create config file {path}: {e}")

    def __repr__(self) -> str:
        return f"Config(config_file={self.config_file}, sections={list(self._config_data.keys())})"
