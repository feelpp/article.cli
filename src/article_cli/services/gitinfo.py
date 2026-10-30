"""
Paper version metadata service for LaTeX and Typst.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Type, Union

from ..command_runner import DEFAULT_RUNNER, CommandRunner
from ..config import Config
from ..git_manager import GitManager
from ..project_context import ProjectContext
from ..paper_version import refresh_typst_metadata, read_git_snapshot
from ..reporting import print_error, print_info, print_success
from .compiler import CompileOptions, CompilerService
from .release import _absolute_pdf_path, pdf_contains_text, write_sha256


@dataclass(frozen=True)
class VersionOptions:
    """User-facing paper version workflow options."""

    dry_run: bool = False
    compile_pdf: bool = False
    check_pdf: bool = False
    checksum: bool = False
    tag: Optional[str] = None
    document: Optional[str] = None
    engine: Optional[str] = None
    output_dir: Optional[str] = None
    shell_escape: Optional[bool] = None


class GitInfoService:
    """Resolve document format, refresh provenance, and validate versioned PDFs."""

    def __init__(
        self,
        config: Optional[Config] = None,
        repo_root: Optional[Path] = None,
        manager_cls: Type[GitManager] = GitManager,
        compiler_service_cls: Type[CompilerService] = CompilerService,
        runner: CommandRunner = DEFAULT_RUNNER,
    ) -> None:
        self.config = config or Config(quiet=True)
        self.manager = (
            manager_cls(repo_root) if repo_root is not None else manager_cls()
        )
        self.compiler_service_cls = compiler_service_cls
        self.runner = runner

    def refresh(self, options: Union[bool, VersionOptions] = False) -> bool:
        """Refresh or preview local gitinfo2 metadata."""
        if isinstance(options, bool):
            return self.manager.refresh_version_metadata(options)

        context = ProjectContext.resolve(
            self.config,
            cwd=self.manager.repo_root,
            document=options.document,
            engine=options.engine,
            output_dir=options.output_dir,
        )
        if options.compile_pdf or options.check_pdf or options.checksum:
            if context.document is None or not context.document.is_file():
                print_error(
                    f"No paper document found in {self.manager.repo_root}. "
                    "Run from the paper repository or select its main file with --document. "
                    "No version metadata was changed."
                )
                return False
        snapshot = None
        if context.is_typst and context.document is not None:
            snapshot = refresh_typst_metadata(context.document.parent, options.dry_run)
            if snapshot is None:
                print_error(
                    "Paper version metadata requires a Git repository with a commit."
                )
                return False
            print_info(f"Git version: {snapshot.description}; branch {snapshot.branch}")
            if options.dry_run:
                print_info("Would refresh gitHeadLocal.json beside the Typst document.")
            else:
                print_success("Refreshed gitHeadLocal.json")
        elif not self.manager.refresh_version_metadata(options.dry_run):
            return False
        elif not options.dry_run and context.document is not None:
            # gitinfo2's local mode also works when the main source is nested.
            source = self.manager.repo_root / "gitHeadLocal.gin"
            target = context.document.parent / "gitHeadLocal.gin"
            if source.is_file() and source != target:
                target.write_bytes(source.read_bytes())

        if options.dry_run:
            self._print_dry_run(options)
            return True

        if options.compile_pdf:
            compiler = self.compiler_service_cls(
                self.config, cwd=self.manager.repo_root
            )
            if not compiler.compile(
                CompileOptions(
                    document=options.document,
                    engine=options.engine,
                    output_dir=options.output_dir,
                    shell_escape=options.shell_escape,
                )
            ):
                return False

        if options.check_pdf:
            expected_text = options.tag or (
                snapshot.description if snapshot else self._current_description()
            )
            if not expected_text:
                print_error("Could not determine a version string for PDF checking.")
                return False
            pdf_path = self._expected_pdf_path(options)
            if not pdf_contains_text(pdf_path, expected_text, self.runner):
                return False

        if options.checksum:
            pdf_path = self._expected_pdf_path(options)
            checksum_path = write_sha256(pdf_path)
            print_success(f"Wrote checksum: {checksum_path}")

        return True

    def _print_dry_run(self, options: VersionOptions) -> None:
        """Print additional dry-run actions for the version workflow."""
        if options.compile_pdf:
            print_info("Would compile the document after refreshing metadata.")
        if options.check_pdf:
            expected = options.tag or self._current_description() or "<git describe>"
            print_info(f"Would verify PDF text contains: {expected}")
        if options.checksum:
            print_info("Would write a PDF sha256 checksum sidecar.")

    def _expected_pdf_path(self, options: VersionOptions) -> Path:
        """Resolve the expected PDF path for version checks."""
        context = ProjectContext.resolve(
            self.config,
            cwd=self.manager.repo_root,
            document=options.document,
            engine=options.engine,
            output_dir=options.output_dir,
            shell_escape=options.shell_escape,
        )
        pdf_path = _absolute_pdf_path(context)
        if pdf_path is None:
            raise ValueError("No PDF path could be resolved for version checking.")
        return pdf_path

    def _current_description(self) -> Optional[str]:
        """Return the current git describe string."""
        snapshot = read_git_snapshot(self.manager.repo_root)
        if snapshot is not None:
            return snapshot.description
        result = self.manager.git(
            ["describe", "--tags", "--long", "--always", "--dirty=-*"]
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
