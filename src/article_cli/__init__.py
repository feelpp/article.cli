"""
Article CLI - A command-line tool for managing LaTeX articles

This package provides tools for:
- Git release management with gitinfo2 support
- Zotero bibliography synchronization
- LaTeX build file cleanup
    - Git hooks setup
"""

__version__ = "1.3.2"
__author__ = "Christophe Prud'homme"
__email__ = "prudhomm@cemosis.fr"

from .cli import main
from .config import Config
from .zotero import ZoteroBibTexUpdater
from .git_manager import GitManager
from .repository_setup import RepositorySetup
from .latex_compiler import LaTeXCompiler

__all__ = [
    "main",
    "Config",
    "ZoteroBibTexUpdater",
    "GitManager",
    "RepositorySetup",
    "LaTeXCompiler",
]
