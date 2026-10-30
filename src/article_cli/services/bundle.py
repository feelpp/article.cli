"""Shared source selection, verification, and archive publication policy."""

import fnmatch
import hashlib
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, List, Mapping, Optional, Set, Tuple

from .. import __version__
from ..command_runner import DEFAULT_RUNNER, CommandRunner
from ..config import Config
from ..project_context import ProjectContext
from .bundle_backends import (
    BundleBackend,
    BundleBuild,
    BundleDependency,
    TEX_JUNK_SUFFIXES,
    default_bundle_backends,
    inside,
)

DEFAULT_EXCLUDES = [
    ".git",
    "**/.git",
    ".git/**",
    "**/.git/**",
    ".venv/**",
    "**/.venv/**",
    "__pycache__/**",
    "**/__pycache__/**",
    "**/local-only/**",
    "**/.env",
    "**/.env.*",
]


@dataclass(frozen=True)
class BundleOptions:
    """Explicit command-line overrides; lists extend project patterns."""

    document: Optional[str] = None
    output: Optional[str] = None
    build_dir: Optional[str] = None
    include: Tuple[str, ...] = ()
    exclude: Tuple[str, ...] = ()
    include_pdf: Optional[bool] = None
    verify: Optional[bool] = None
    no_build: bool = False
    dry_run: bool = False


@dataclass
class BundlePlan:
    """Selected source paths keyed by their names in the archive."""

    root: Path
    document: str
    output: Path
    files: Dict[str, Path]
    engine: str
    verify: bool
    build_dir: Path
    timeout: int
    font_paths: Tuple[str, ...] = ()

    def manifest(self, payloads: Dict[str, bytes]) -> Dict:
        """Return portable, deterministic provenance without absolute paths."""
        return {
            "article_cli_version": __version__,
            "document": self.document,
            "engine": self.engine,
            "font_paths": list(self.font_paths),
            "files": [
                {
                    "path": name,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                for name, data in payloads.items()
            ],
        }


def _pattern(value: str) -> str:
    if (
        not value
        or "\\" in value
        or Path(value).is_absolute()
        or ".." in PurePosixPath(value).parts
        or ":" in value
    ):
        raise ValueError(
            f"Bundle patterns must stay inside the document directory: {value!r}"
        )
    return value.removeprefix("./")


def _matches(name: str, pattern: str) -> bool:
    """Match root-relative globs, including zero-directory ** matches."""
    names = PurePosixPath(name).parts
    patterns = PurePosixPath(pattern).parts

    def match(i: int, j: int) -> bool:
        if j == len(patterns):
            return i == len(names)
        if patterns[j] == "**":
            return match(i, j + 1) or (i < len(names) and match(i + 1, j))
        return (
            i < len(names)
            and fnmatch.fnmatchcase(names[i], patterns[j])
            and match(i + 1, j + 1)
        )

    return match(0, 0)


class BundleService:
    """Collect dependencies, apply project policy, verify, and write a ZIP."""

    def __init__(
        self,
        config: Config,
        cwd: Optional[Path] = None,
        runner: CommandRunner = DEFAULT_RUNNER,
        backends: Optional[Mapping[str, BundleBackend]] = None,
    ):
        self.config = config
        self.cwd = (cwd or Path.cwd()).resolve()
        self.backends = (
            default_bundle_backends(runner) if backends is None else backends
        )

    def plan(self, options: BundleOptions) -> BundlePlan:
        policy = self.config.get_bundle_config()
        context = ProjectContext.resolve(
            self.config, cwd=self.cwd, document=options.document
        )
        document = context.document
        if document is None or not document.is_file():
            raise ValueError("Bundle requires an existing main .tex or .typ document.")
        backend = self.backends.get(context.engine)
        if backend is None or document.suffix != backend.suffix:
            raise ValueError(
                f"Unsupported bundle document/engine: {document.suffix}/{context.engine}"
            )
        # Root the ZIP at the main document directory, as archive services compile there.
        root = document.parent.resolve()
        build_value = (
            options.build_dir or context.output_dir_name or ".article-cli/bundle-build"
        )
        build_dir = (root / build_value).resolve()
        if not inside(build_dir, root):
            raise ValueError(
                "Bundle build directory must stay inside the document directory."
            )
        output_value = (
            options.output or policy["output"] or f"dist/{document.stem}-sources.zip"
        )
        output = (root / output_value).resolve()
        if output.suffix.lower() != ".zip":
            raise ValueError("Bundle output must have a .zip extension.")
        timeout = int(self.config.get_latex_config().get("timeout", 300))
        include = self._patterns(policy["include"], "include") + list(options.include)
        exclude = (
            DEFAULT_EXCLUDES
            + self._patterns(policy["exclude"], "exclude")
            + list(options.exclude)
        )
        include = [_pattern(p) for p in include]
        exclude = [
            _pattern(p.rstrip("/") + "/**" if (root / p).is_dir() else p)
            for p in exclude
        ]
        include_pdf = (
            options.include_pdf
            if options.include_pdf is not None
            else policy["include_pdf"]
        )
        verify = options.verify if options.verify is not None else policy["verify"]
        if not isinstance(include_pdf, bool) or not isinstance(verify, bool):
            raise ValueError("bundle.include_pdf and bundle.verify must be booleans.")
        font_paths = self._font_paths(root) if context.is_typst else ()
        build = BundleBuild(document, build_dir, timeout, font_paths)
        if not options.no_build and not options.dry_run:
            backend.compile(build)
        files: Dict[str, Path] = {}
        required: Set[str] = set()
        main_pdf = build_dir / document.with_suffix(".pdf").name
        reserved = {output, output.with_suffix(".manifest.json")}

        def add(dependency: BundleDependency, needed: bool = False) -> None:
            path = dependency.source
            name = _pattern(dependency.name)
            resolved = path.resolve()
            if resolved in reserved or (
                resolved == main_pdf.resolve() and not include_pdf
            ):
                return
            if not inside(resolved, dependency.source_root.resolve()):
                raise ValueError(
                    f"Cannot bundle a dependency outside the document directory: {path}"
                )
            blocked = any(_matches(name, p) for p in exclude)
            # Backends have already removed their own compiler artifacts.
            # Required inputs may legitimately use a log-like suffix (e.g. read("data.log")).
            junk = not needed and (
                path.suffix in TEX_JUNK_SUFFIXES
                or name.endswith((".synctex.gz", ".typst-deps.json", ".run.xml"))
            )
            if blocked or junk:
                if needed:
                    raise ValueError(
                        f"Required dependency excluded from bundle: {name}"
                    )
                return
            if not path.is_file():
                raise ValueError(f"Missing bundle dependency: {path}")
            if name in files and files[name].resolve() != resolved:
                raise ValueError(
                    f"Two dependencies map to the same archive path: {name}"
                )
            files[name] = path
            if needed:
                required.add(name)

        add(BundleDependency(document, document.name, root), needed=True)
        for dependency in backend.dependencies(build):
            add(dependency, needed=True)
        # Broad includes must not reintroduce stale main PDFs or compiler-output
        # aliases for dependencies already placed at their portable archive paths.
        automatic_sources = {path.resolve() for path in files.values()}
        main_pdf_sources = {main_pdf.resolve(), document.with_suffix(".pdf").resolve()}
        for pattern in include:
            matches = list(root.glob(pattern))
            if not matches:
                raise ValueError(f"Include pattern matched no files: {pattern}")
            for match in matches:
                paths = match.rglob("*") if match.is_dir() else [match]
                for path in paths:
                    if (
                        path.is_file()
                        and path.resolve() not in automatic_sources
                        and path.resolve() not in main_pdf_sources
                    ):
                        add(
                            BundleDependency(
                                path, path.relative_to(root).as_posix(), root
                            )
                        )
        if include_pdf:
            add(BundleDependency(main_pdf, main_pdf.name, root))
        if not files or document.name not in required:
            raise ValueError("Bundle must include its main document.")
        return BundlePlan(
            root,
            document.name,
            output,
            files,
            context.engine,
            bool(verify),
            build_dir,
            timeout,
            font_paths,
        )

    def _font_paths(self, root: Path) -> Tuple[str, ...]:
        values = self._patterns(
            self.config.get_typst_config()["font_paths"], "font_paths"
        )
        result = []
        for value in values:
            path = (root / value).resolve()
            if not inside(path, root):
                raise ValueError(
                    f"Typst font directories must stay inside the document directory: {value}"
                )
            if not path.is_dir():
                raise ValueError(f"Missing Typst font directory: {value}")
            result.append(path.relative_to(root).as_posix())
        return tuple(result)

    @staticmethod
    def _patterns(value: object, key: str) -> List[str]:
        if not isinstance(value, list) or any(not isinstance(p, str) for p in value):
            raise ValueError(f"bundle.{key} must be a list of glob strings.")
        return value

    def write(self, plan: BundlePlan, force: bool = False) -> Path:
        """Publish the ZIP only after its selected sources pass requested verification."""
        manifest_path = plan.output.with_suffix(".manifest.json")
        if not force and (plan.output.exists() or manifest_path.exists()):
            raise ValueError("Bundle output already exists; use --force to replace it.")
        payloads = {
            name: path.read_bytes() for name, path in sorted(plan.files.items())
        }
        if plan.verify:
            with tempfile.TemporaryDirectory(prefix="article-cli-bundle-") as directory:
                stage = Path(directory)
                for name, data in payloads.items():
                    dest = stage / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                self.backends[plan.engine].compile(
                    BundleBuild(
                        stage / plan.document,
                        stage / ".verify-build",
                        plan.timeout,
                        plan.font_paths,
                    )
                )
        plan.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=plan.output.parent) as directory:
            archive = Path(directory) / "bundle.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
                for name, data in payloads.items():
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    z.writestr(info, data)
            manifest = plan.manifest(payloads)
            manifest["verified"] = plan.verify
            manifest["archive_sha256"] = hashlib.sha256(
                archive.read_bytes()
            ).hexdigest()
            staged_manifest = Path(directory) / "manifest.json"
            staged_manifest.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            )
            os.replace(archive, plan.output)
            os.replace(staged_manifest, manifest_path)
        return plan.output
