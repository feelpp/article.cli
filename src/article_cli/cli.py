"""
Main CLI interface for article-cli

Provides command-line interface for managing LaTeX articles with git and Zotero integration.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .config import Config
from .zotero import ZoteroBibTexUpdater, print_error, print_info
from .git_manager import GitManager
from .repository_setup import RepositorySetup


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        prog="article-cli",
        description="CLI tool for managing LaTeX articles with git and Zotero integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init --title "My Article" --authors "John Doe,Jane Smith"
  %(prog)s setup                          # Setup git hooks
  %(prog)s clean                          # Clean build files
  %(prog)s compile main.tex               # Compile with latexmk
  %(prog)s compile --engine pdflatex      # Compile with pdflatex
  %(prog)s compile --shell-escape         # Enable shell escape
  %(prog)s compile --watch                # Watch and auto-recompile
  %(prog)s create v1.0.0                  # Create release v1.0.0
  %(prog)s list --count 10                # List 10 recent releases
  %(prog)s delete v1.0.0                  # Delete release
  %(prog)s update-bibtex                  # Update from Zotero
  %(prog)s config create                  # Create sample config file
  %(prog)s install-fonts                  # Install fonts for XeLaTeX
  %(prog)s install-fonts --list           # List installed fonts
  %(prog)s install-theme numpex           # Install numpex Beamer theme
  %(prog)s install-theme --list           # List available themes

Environment variables:
  ZOTERO_API_KEY    : Your Zotero API key (required for update-bibtex)
  ZOTERO_USER_ID    : Your Zotero user ID
  ZOTERO_GROUP_ID   : Your Zotero group ID
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument("--config", type=Path, help="Path to configuration file")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize repository with workflows and configuration"
    )
    init_parser.add_argument("--title", required=True, help="Article title")
    init_parser.add_argument(
        "--authors",
        required=True,
        help='Comma-separated list of authors (e.g., "John Doe,Jane Smith")',
    )
    init_parser.add_argument(
        "--group-id",
        default="4678293",
        help="Zotero group ID (default: 4678293 for article.template)",
    )
    init_parser.add_argument(
        "--tex-file",
        help="Main .tex file (auto-detected if not specified)",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    init_parser.add_argument(
        "--type",
        choices=["article", "presentation", "poster"],
        default="article",
        help="Project type (default: article). Use 'presentation' for Beamer slides.",
    )
    init_parser.add_argument(
        "--theme",
        default="",
        help="Beamer theme for presentations (e.g., 'numpex', 'metropolis').",
    )
    init_parser.add_argument(
        "--aspect-ratio",
        choices=["169", "43", "1610"],
        default="169",
        help="Aspect ratio for presentations (default: 169 for 16:9).",
    )

    # Setup command
    subparsers.add_parser("setup", help="Setup git hooks for gitinfo2")

    # Clean command
    subparsers.add_parser("clean", help="Clean LaTeX build files")

    # Compile command
    compile_parser = subparsers.add_parser(
        "compile", help="Compile LaTeX document using latexmk"
    )
    compile_parser.add_argument(
        "tex_file",
        nargs="?",
        help="LaTeX file to compile (auto-detected if not specified)",
    )
    compile_parser.add_argument(
        "--engine",
        choices=["latexmk", "pdflatex", "xelatex", "lualatex"],
        default="latexmk",
        help="LaTeX engine to use (default: latexmk). Use xelatex/lualatex for custom fonts.",
    )
    compile_parser.add_argument(
        "--shell-escape",
        action="store_true",
        help="Enable shell escape (for code highlighting, etc.)",
    )
    compile_parser.add_argument(
        "--clean-first",
        action="store_true",
        help="Clean build files before compilation",
    )
    compile_parser.add_argument(
        "--clean-after", action="store_true", help="Clean build files after compilation"
    )
    compile_parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for changes and recompile automatically",
    )
    compile_parser.add_argument(
        "--output-dir", help="Output directory for compiled files"
    )

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new release")
    create_parser.add_argument("version", help="Version tag (e.g., v1.0.0)")
    create_parser.add_argument(
        "--push", action="store_true", help="Automatically push the release"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List releases")
    list_parser.add_argument(
        "--count", type=int, default=5, help="Number of releases to show"
    )

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a release")
    delete_parser.add_argument("version", help="Version tag to delete")
    delete_parser.add_argument(
        "--remote", action="store_true", help="Also delete from remote"
    )

    # Update-bibtex command
    bibtex_parser = subparsers.add_parser(
        "update-bibtex", help="Update BibTeX from Zotero"
    )
    bibtex_parser.add_argument("--api-key", help="Zotero API key")
    bibtex_parser.add_argument("--user-id", help="Zotero user ID")
    bibtex_parser.add_argument("--group-id", help="Zotero group ID")
    bibtex_parser.add_argument(
        "--output", default="references.bib", help="Output BibTeX file"
    )
    bibtex_parser.add_argument(
        "--no-backup", action="store_true", help="Skip backup creation"
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Config subcommands"
    )

    config_create_parser = config_subparsers.add_parser(
        "create", help="Create sample configuration file"
    )
    config_create_parser.add_argument("--path", type=Path, help="Path for config file")

    config_subparsers.add_parser("show", help="Show current configuration")

    # Install-fonts command
    fonts_parser = subparsers.add_parser(
        "install-fonts", help="Download and install fonts for XeLaTeX projects"
    )
    fonts_parser.add_argument(
        "--dir",
        type=Path,
        help="Directory to install fonts (default: fonts/)",
    )
    fonts_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download fonts even if already installed",
    )
    fonts_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_fonts",
        help="List installed fonts instead of installing",
    )

    # Install-theme command
    theme_parser = subparsers.add_parser(
        "install-theme", help="Download and install Beamer themes for presentations"
    )
    theme_parser.add_argument(
        "theme_name",
        nargs="?",
        help="Name of theme to install (e.g., 'numpex')",
    )
    theme_parser.add_argument(
        "--dir",
        type=Path,
        help="Directory to install theme (default: current directory)",
    )
    theme_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download theme even if already installed",
    )
    theme_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_themes",
        help="List available themes instead of installing",
    )
    theme_parser.add_argument(
        "--url",
        help="Custom URL to download theme from (use with theme_name)",
    )

    return parser


def handle_init_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the init command"""
    try:
        # Parse comma-separated authors
        authors = [a.strip() for a in args.authors.split(",")]

        repo_setup = RepositorySetup()
        return (
            0
            if repo_setup.init_repository(
                title=args.title,
                authors=authors,
                group_id=args.group_id,
                force=args.force,
                main_tex_file=args.tex_file,
                project_type=args.type,
                theme=args.theme,
                aspect_ratio=args.aspect_ratio,
            )
            else 1
        )
    except Exception as e:
        print_error(f"Failed to initialize repository: {e}")
        return 1


def handle_setup_command(config: Config) -> int:
    """Handle the setup command"""
    try:
        git_manager = GitManager()
        return 0 if git_manager.setup_hooks() else 1
    except ValueError as e:
        print_error(str(e))
        return 1


def handle_clean_command(config: Config) -> int:
    """Handle the clean command"""
    try:
        git_manager = GitManager()
        latex_config = config.get_latex_config()
        return (
            0 if git_manager.clean_latex_files(latex_config["clean_extensions"]) else 1
        )
    except ValueError as e:
        print_error(str(e))
        return 1


def handle_compile_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the compile command"""
    try:
        from .latex_compiler import LaTeXCompiler

        # Auto-detect tex file if not provided
        tex_file = args.tex_file
        if not tex_file:
            tex_file = _auto_detect_tex_file()
            if not tex_file:
                print_error(
                    "No .tex file specified and none found in current directory"
                )
                return 1

        # Validate tex file exists
        tex_path = Path(tex_file)
        if not tex_path.exists():
            print_error(f"LaTeX file not found: {tex_file}")
            return 1

        compiler = LaTeXCompiler(config)

        # Clean before compilation if requested
        if args.clean_first:
            print_info("Cleaning build files before compilation...")
            git_manager = GitManager()
            latex_config = config.get_latex_config()
            git_manager.clean_latex_files(latex_config["clean_extensions"])

        # Compile the document
        success = compiler.compile(
            tex_file=tex_file,
            engine=args.engine,
            shell_escape=args.shell_escape,
            output_dir=args.output_dir,
            watch=args.watch,
        )

        # Clean after compilation if requested
        if args.clean_after and success:
            print_info("Cleaning build files after compilation...")
            git_manager = GitManager()
            latex_config = config.get_latex_config()
            git_manager.clean_latex_files(latex_config["clean_extensions"])

        return 0 if success else 1

    except Exception as e:
        print_error(f"Compilation failed: {e}")
        return 1


def _auto_detect_tex_file() -> Optional[str]:
    """Auto-detect main .tex file in current directory"""
    current_dir = Path.cwd()
    tex_files = list(current_dir.glob("*.tex"))

    if not tex_files:
        return None

    if len(tex_files) == 1:
        return tex_files[0].name

    # Multiple .tex files - prefer common patterns
    for pattern in ["main.tex", "article.tex", f"{current_dir.name}.tex"]:
        if (current_dir / pattern).exists():
            return pattern

    # Return first .tex file found
    print_info(f"Multiple .tex files found, using: {tex_files[0].name}")
    return tex_files[0].name


def handle_create_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the create command"""
    try:
        git_manager = GitManager()
        git_config = config.get_git_config()
        auto_push = args.push or git_config.get("auto_push", False)
        return 0 if git_manager.create_release(args.version, auto_push) else 1
    except ValueError as e:
        print_error(str(e))
        return 1


def handle_list_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the list command"""
    try:
        git_manager = GitManager()
        return 0 if git_manager.list_releases(args.count) else 1
    except ValueError as e:
        print_error(str(e))
        return 1


def handle_delete_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the delete command"""
    try:
        git_manager = GitManager()
        return 0 if git_manager.delete_release(args.version, args.remote) else 1
    except ValueError as e:
        print_error(str(e))
        return 1


def handle_update_bibtex_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the update-bibtex command"""
    try:
        # Get and validate Zotero configuration
        zotero_config = config.validate_zotero_config(args)

        updater = ZoteroBibTexUpdater(
            api_key=zotero_config["api_key"],
            user_id=zotero_config["user_id"],
            group_id=zotero_config["group_id"],
            output_file=zotero_config["output_file"],
        )

        return 0 if updater.update(backup=not args.no_backup) else 1

    except ValueError as e:
        print_error(str(e))
        return 1


def handle_config_command(args: argparse.Namespace, config: Config) -> int:
    """Handle config subcommands"""
    if args.config_command == "create":
        try:
            path = args.path or Path.cwd() / ".article-cli.toml"
            config.create_sample_config(path)
            return 0
        except Exception as e:
            print_error(f"Failed to create config file: {e}")
            return 1

    elif args.config_command == "show":
        try:
            print_info("Current configuration:")
            zotero_config = config.get_zotero_config()
            git_config = config.get_git_config()
            latex_config = config.get_latex_config()

            print("\n[Zotero]")
            print(f"  API Key: {'***' if zotero_config['api_key'] else 'Not set'}")
            print(f"  User ID: {zotero_config['user_id'] or 'Not set'}")

            # Show group ID with name if available
            if zotero_config["group_id"]:
                group_display = zotero_config["group_id"]

                # Try to get group name if API key is available
                if zotero_config["api_key"]:
                    try:
                        from .zotero import ZoteroBibTexUpdater

                        updater = ZoteroBibTexUpdater(
                            api_key=zotero_config["api_key"],
                            group_id=zotero_config["group_id"],
                        )
                        group_name = updater.get_group_name()
                        if group_name:
                            group_display = (
                                f"{zotero_config['group_id']} ({group_name})"
                            )
                    except Exception:
                        pass  # Silently fall back to just showing ID

                print(f"  Group ID: {group_display}")
            else:
                print(f"  Group ID: Not set")

            print(f"  Output File: {zotero_config['output_file']}")

            print("\n[Git]")
            print(f"  Auto Push: {git_config['auto_push']}")
            print(f"  Default Branch: {git_config['default_branch']}")

            print("\n[LaTeX]")
            print(
                f"  Clean Extensions: {len(latex_config['clean_extensions'])} extensions"
            )
            print(f"  Build Directory: {latex_config['build_dir']}")
            print(f"  Engine: {latex_config['engine']}")
            print(f"  Shell Escape: {latex_config['shell_escape']}")
            print(f"  Timeout: {latex_config['timeout']}s")

            return 0
        except Exception as e:
            print_error(f"Failed to show configuration: {e}")
            return 1
    else:
        print_error("Unknown config command")
        return 1


def handle_install_fonts_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the install-fonts command"""
    try:
        from .fonts import FontInstaller, install_fonts_from_config

        fonts_config = config.get_fonts_config()

        # Override directory if specified on command line
        fonts_dir = (
            args.dir if args.dir else Path(fonts_config.get("directory", "fonts"))
        )

        # List installed fonts if requested
        if args.list_fonts:
            installer = FontInstaller(fonts_dir=fonts_dir)
            installed = installer.list_installed()

            if not installed:
                print_info(f"No fonts installed in {fonts_dir}")
                return 0

            print_info(f"Installed fonts in {fonts_dir}:")
            for font_name in installed:
                font_files = installer.get_font_files(font_name)
                print(f"  - {font_name} ({len(font_files)} font files)")

            return 0

        # Install fonts
        sources = fonts_config.get("sources", [])
        installer = FontInstaller(fonts_dir=fonts_dir, sources=sources)

        success = installer.install_all(force=args.force)
        return 0 if success else 1

    except Exception as e:
        print_error(f"Font installation failed: {e}")
        return 1


def handle_install_theme_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the install-theme command"""
    try:
        from .themes import ThemeInstaller

        themes_config = config.get_themes_config()

        # Override directory if specified on command line
        themes_dir = args.dir if args.dir else Path(themes_config.get("directory", "."))

        # Get configured sources
        sources = themes_config.get("sources", {})

        installer = ThemeInstaller(themes_dir=themes_dir, sources=sources)

        # List available themes if requested
        if args.list_themes:
            available = installer.list_available()
            installed = installer.list_installed()

            print_info("Available themes:")
            for theme in available:
                name = theme["name"]
                desc = theme.get("description", "")
                engine = theme.get("engine", "pdflatex")
                fonts = (
                    " (requires custom fonts)" if theme.get("requires_fonts") else ""
                )
                installed_marker = (
                    " [installed]" if any(i["name"] == name for i in installed) else ""
                )
                print(f"  - {name}: {desc}")
                print(f"      Engine: {engine}{fonts}{installed_marker}")

            return 0

        # Theme name is required for installation
        if not args.theme_name:
            print_error("Theme name is required. Use --list to see available themes.")
            return 1

        # Install from custom URL if provided
        if args.url:
            success = installer.install_from_url(
                name=args.theme_name,
                url=args.url,
                force=args.force,
            )
        else:
            # Install from known sources
            success = installer.install_theme(
                name=args.theme_name,
                force=args.force,
            )

        return 0 if success else 1

    except Exception as e:
        print_error(f"Theme installation failed: {e}")
        return 1


def main(argv: Optional[list] = None) -> int:
    """
    Main entry point for article-cli

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    # Initialize configuration
    try:
        config = Config(args.config)
    except Exception as e:
        print_error(f"Configuration error: {e}")
        return 1

    # Route to appropriate command handler
    try:
        if args.command == "init":
            return handle_init_command(args, config)

        elif args.command == "setup":
            return handle_setup_command(config)

        elif args.command == "clean":
            return handle_clean_command(config)

        elif args.command == "compile":
            return handle_compile_command(args, config)

        elif args.command == "create":
            return handle_create_command(args, config)

        elif args.command == "list":
            return handle_list_command(args, config)

        elif args.command == "delete":
            return handle_delete_command(args, config)

        elif args.command == "update-bibtex":
            return handle_update_bibtex_command(args, config)

        elif args.command == "config":
            return handle_config_command(args, config)

        elif args.command == "install-fonts":
            return handle_install_fonts_command(args, config)

        elif args.command == "install-theme":
            return handle_install_theme_command(args, config)

        else:
            print_error(f"Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
