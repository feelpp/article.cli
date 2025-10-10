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
from .zotero import ZoteroBibTexUpdater, print_success, print_error, print_warning, print_info
from .git_manager import GitManager


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        prog='article-cli',
        description='CLI tool for managing LaTeX articles with git and Zotero integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s setup                          # Setup git hooks
  %(prog)s clean                          # Clean build files
  %(prog)s create v1.0.0                  # Create release v1.0.0
  %(prog)s list --count 10                # List 10 recent releases
  %(prog)s delete v1.0.0                  # Delete release
  %(prog)s update-bibtex                  # Update from Zotero
  %(prog)s config create                  # Create sample config file

Environment variables:
  ZOTERO_API_KEY    : Your Zotero API key (required for update-bibtex)
  ZOTERO_USER_ID    : Your Zotero user ID
  ZOTERO_GROUP_ID   : Your Zotero group ID
        """
    )

    parser.add_argument(
        '--version', 
        action='version', 
        version=f'%(prog)s {__version__}'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to configuration file'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Setup command
    subparsers.add_parser('setup', help='Setup git hooks for gitinfo2')

    # Clean command
    subparsers.add_parser('clean', help='Clean LaTeX build files')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new release')
    create_parser.add_argument('version', help='Version tag (e.g., v1.0.0)')
    create_parser.add_argument('--push', action='store_true', help='Automatically push the release')

    # List command
    list_parser = subparsers.add_parser('list', help='List releases')
    list_parser.add_argument('--count', type=int, default=5, help='Number of releases to show')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a release')
    delete_parser.add_argument('version', help='Version tag to delete')
    delete_parser.add_argument('--remote', action='store_true', help='Also delete from remote')

    # Update-bibtex command
    bibtex_parser = subparsers.add_parser('update-bibtex', help='Update BibTeX from Zotero')
    bibtex_parser.add_argument('--api-key', help='Zotero API key')
    bibtex_parser.add_argument('--user-id', help='Zotero user ID')
    bibtex_parser.add_argument('--group-id', help='Zotero group ID')
    bibtex_parser.add_argument('--output', default='references.bib', help='Output BibTeX file')
    bibtex_parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')

    # Config command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_subparsers = config_parser.add_subparsers(dest='config_command', help='Config subcommands')
    
    config_create_parser = config_subparsers.add_parser('create', help='Create sample configuration file')
    config_create_parser.add_argument('--path', type=Path, help='Path for config file')
    
    config_subparsers.add_parser('show', help='Show current configuration')

    return parser


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
        return 0 if git_manager.clean_latex_files(latex_config['clean_extensions']) else 1
    except ValueError as e:
        print_error(str(e))
        return 1


def handle_create_command(args: argparse.Namespace, config: Config) -> int:
    """Handle the create command"""
    try:
        git_manager = GitManager()
        git_config = config.get_git_config()
        auto_push = args.push or git_config.get('auto_push', False)
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
            api_key=zotero_config['api_key'],
            user_id=zotero_config['user_id'],
            group_id=zotero_config['group_id'],
            output_file=zotero_config['output_file']
        )

        return 0 if updater.update(backup=not args.no_backup) else 1
        
    except ValueError as e:
        print_error(str(e))
        return 1


def handle_config_command(args: argparse.Namespace, config: Config) -> int:
    """Handle config subcommands"""
    if args.config_command == 'create':
        try:
            path = args.path or Path.cwd() / '.article-cli.toml'
            config.create_sample_config(path)
            return 0
        except Exception as e:
            print_error(f"Failed to create config file: {e}")
            return 1
            
    elif args.config_command == 'show':
        try:
            print_info("Current configuration:")
            zotero_config = config.get_zotero_config()
            git_config = config.get_git_config()
            latex_config = config.get_latex_config()
            
            print("\n[Zotero]")
            print(f"  API Key: {'***' if zotero_config['api_key'] else 'Not set'}")
            print(f"  User ID: {zotero_config['user_id'] or 'Not set'}")
            
            # Show group ID with name if available
            if zotero_config['group_id']:
                group_display = zotero_config['group_id']
                
                # Try to get group name if API key is available
                if zotero_config['api_key']:
                    try:
                        from .zotero import ZoteroBibTexUpdater
                        updater = ZoteroBibTexUpdater(
                            api_key=zotero_config['api_key'],
                            group_id=zotero_config['group_id']
                        )
                        group_name = updater.get_group_name()
                        if group_name:
                            group_display = f"{zotero_config['group_id']} ({group_name})"
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
            print(f"  Clean Extensions: {len(latex_config['clean_extensions'])} extensions")
            print(f"  Build Directory: {latex_config['build_dir']}")
            
            return 0
        except Exception as e:
            print_error(f"Failed to show configuration: {e}")
            return 1
    else:
        print_error("Unknown config command")
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
        if args.command == 'setup':
            return handle_setup_command(config)
        
        elif args.command == 'clean':
            return handle_clean_command(config)
            
        elif args.command == 'create':
            return handle_create_command(args, config)
            
        elif args.command == 'list':
            return handle_list_command(args, config)
            
        elif args.command == 'delete':
            return handle_delete_command(args, config)
            
        elif args.command == 'update-bibtex':
            return handle_update_bibtex_command(args, config)
            
        elif args.command == 'config':
            return handle_config_command(args, config)
            
        else:
            print_error(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())