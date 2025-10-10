"""
Git operations and release management

Handles git hooks setup, release creation, and LaTeX build file cleanup.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Optional
import shutil

from .zotero import print_success, print_error, print_warning, print_info, Colors


class GitManager:
    """Git operations manager for article repositories"""

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize Git manager

        Args:
            repo_root: Repository root directory (defaults to current directory)
        """
        self.repo_root = repo_root or Path.cwd()
        self._validate_git_repo()

    def _validate_git_repo(self) -> None:
        """Validate that the current directory is a git repository"""
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.repo_root}")

    def setup_hooks(self) -> bool:
        """Setup git hooks for gitinfo2"""
        try:
            hooks_dir = self.repo_root / "hooks"
            git_hooks_dir = self.repo_root / ".git" / "hooks"

            if not hooks_dir.exists():
                print_error(f"Hooks directory not found: {hooks_dir}")
                return False

            if not git_hooks_dir.exists():
                print_error("Git hooks directory missing")
                return False

            post_commit_src = hooks_dir / "post-commit"
            if not post_commit_src.exists():
                print_error(f"Source hook not found: {post_commit_src}")
                return False

            # Copy and make executable
            for hook_name in ["post-commit", "post-checkout", "post-merge"]:
                dest = git_hooks_dir / hook_name

                with open(post_commit_src, "r") as src:
                    with open(dest, "w") as dst:
                        dst.write(src.read())

                dest.chmod(0o755)
                print_success(f"Installed hook: {hook_name}")

            # Run git checkout to trigger hooks
            subprocess.run(["git", "checkout"], check=True, cwd=self.repo_root)

            # Check for gitHeadInfo.gin
            git_head_info = self.repo_root / ".git" / "gitHeadInfo.gin"
            if not git_head_info.exists():
                print_warning("gitHeadInfo.gin not found, skipping local copy")
            else:
                local_copy = self.repo_root / "gitHeadLocal.gin"
                with open(git_head_info, "r") as src:
                    with open(local_copy, "w") as dst:
                        dst.write(src.read())

                subprocess.run(
                    ["git", "add", "gitHeadLocal.gin"], check=True, cwd=self.repo_root
                )
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        "Created gitHeadLocal.gin for initial setup",
                    ],
                    check=True,
                    cwd=self.repo_root,
                )
                print_success("Created and committed gitHeadLocal.gin")

            return True

        except subprocess.CalledProcessError as e:
            print_error(f"Git command failed: {e}")
            return False
        except Exception as e:
            print_error(f"Failed to setup hooks: {e}")
            return False

    def create_release(self, version: str, auto_push: bool = False) -> bool:
        """
        Create a new release with the given version

        Args:
            version: Version string (e.g., 'v1.0.0')
            auto_push: Whether to automatically push the release

        Returns:
            True if successful, False otherwise
        """
        # Validate version format
        if not re.match(r"^v\d+\.\d+\.\d+(-[a-z]+\.\d+)?$", version):
            print_error(f"Invalid version format: {version}")
            print_info("Expected format: vX.Y.Z or vX.Y.Z-pre.N")
            return False

        try:
            # Check if tag exists
            result = subprocess.run(
                ["git", "rev-parse", version], capture_output=True, cwd=self.repo_root
            )
            if result.returncode == 0:
                print_error(f"Tag {version} already exists")
                return False

            # Create tag
            subprocess.run(
                ["git", "tag", "-a", version, "-m", f"Release {version}"],
                check=True,
                cwd=self.repo_root,
            )
            print_success(f"Created tag: {version}")

            # Trigger hooks
            subprocess.run(["git", "checkout"], check=True, cwd=self.repo_root)

            # Copy gitHeadInfo
            git_head_info = self.repo_root / ".git" / "gitHeadInfo.gin"
            if git_head_info.exists():
                local_copy = self.repo_root / "gitHeadLocal.gin"
                with open(git_head_info, "r") as src:
                    content = src.read()
                    with open(local_copy, "w") as dst:
                        dst.write(content)

                    # Show reltag
                    for line in content.split("\n"):
                        if "reltag" in line:
                            print_info(f"Release tag: {line}")

                subprocess.run(
                    ["git", "add", "gitHeadLocal.gin"], check=True, cwd=self.repo_root
                )
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"Updated gitHeadLocal.gin for release {version}",
                    ],
                    check=True,
                    cwd=self.repo_root,
                )
                subprocess.run(
                    ["git", "tag", "-f", "-a", version, "-m", f"Release {version}"],
                    check=True,
                    cwd=self.repo_root,
                )

            print_success(f"Release {version} created successfully")

            if auto_push:
                try:
                    subprocess.run(
                        ["git", "push", "origin", "--follow-tags"],
                        check=True,
                        cwd=self.repo_root,
                    )
                    print_success("Release pushed to remote")
                except subprocess.CalledProcessError as e:
                    print_warning(f"Failed to push release: {e}")
                    print_info("Push manually with: git push origin --follow-tags")
            else:
                print_info("Push with: git push origin --follow-tags")

            return True

        except subprocess.CalledProcessError as e:
            print_error(f"Git command failed: {e}")
            return False
        except Exception as e:
            print_error(f"Failed to create release: {e}")
            return False

    def list_releases(self, count: int = 5) -> bool:
        """
        List recent releases

        Args:
            count: Number of releases to show

        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "tag", "--sort=-creatordate"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root,
            )

            tags = result.stdout.strip().split("\n")
            if not tags or tags == [""]:
                print_info("No releases found")
                return True

            print(f"\n{Colors.BOLD}Recent releases:{Colors.ENDC}")
            for i, tag in enumerate(tags[:count], 1):
                print(f"  {i}. {tag}")

            if len(tags) > count:
                print(f"  ... and {len(tags) - count} more")

            return True

        except subprocess.CalledProcessError as e:
            print_error(f"Failed to list releases: {e}")
            return False

    def delete_release(self, version: str, delete_remote: bool = False) -> bool:
        """
        Delete a release tag

        Args:
            version: Version tag to delete
            delete_remote: Whether to also delete from remote

        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ["git", "tag", "-d", version], check=True, cwd=self.repo_root
            )
            print_success(f"Deleted local tag: {version}")

            if delete_remote:
                try:
                    subprocess.run(
                        ["git", "push", "origin", "--delete", version],
                        check=True,
                        cwd=self.repo_root,
                    )
                    print_success(f"Deleted remote tag: {version}")
                except subprocess.CalledProcessError as e:
                    print_warning(f"Failed to delete remote tag: {e}")
                    print_info(
                        f"Delete manually with: git push origin --delete {version}"
                    )
            else:
                print_info(f"To delete remote: git push origin --delete {version}")

            return True

        except subprocess.CalledProcessError as e:
            print_error(f"Failed to delete tag: {e}")
            return False

    def clean_latex_files(self, extensions: Optional[List[str]] = None) -> bool:
        """
        Clean LaTeX build files

        Args:
            extensions: List of file extensions to clean (defaults to common LaTeX files)

        Returns:
            True if successful, False otherwise
        """
        if extensions is None:
            extensions = [
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

        removed_count = 0

        # Remove files by extension
        for ext in extensions:
            for file in self.repo_root.glob(f"*{ext}"):
                try:
                    file.unlink()
                    removed_count += 1
                except Exception as e:
                    print_warning(f"Could not remove {file}: {e}")

        # Remove _minted directories
        for minted_dir in self.repo_root.glob("_minted-*"):
            if minted_dir.is_dir():
                try:
                    shutil.rmtree(minted_dir)
                    removed_count += 1
                except Exception as e:
                    print_warning(f"Could not remove {minted_dir}: {e}")

        if removed_count > 0:
            print_success(f"Removed {removed_count} build file(s)")
        else:
            print_info("No build files to clean")

        return True

    def get_current_branch(self) -> Optional[str]:
        """Get the current git branch name"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def is_clean_working_directory(self) -> bool:
        """Check if the working directory is clean (no uncommitted changes)"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root,
            )
            return len(result.stdout.strip()) == 0
        except subprocess.CalledProcessError:
            return False
