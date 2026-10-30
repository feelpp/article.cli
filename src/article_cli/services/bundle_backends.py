"""Compiler strategies for source bundles, independent of archive policy.

A backend compiles a build request and reports required files with portable ZIP
names. BundleService owns selection policy, verification, and publication. New
backends can implement the protocol without inheriting a service implementation.
"""

import json
import os
import re
import tomllib
from xml.etree import ElementTree
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional, Protocol, Tuple

from ..command_runner import CommandRunner
from ..project_context import LATEX_ENGINES

TYPST_PACKAGES = ".article-cli/typst-packages"
TEX_JUNK_SUFFIXES = {
    ".aux",
    ".log",
    ".out",
    ".fls",
    ".blg",
    ".bcf",
    ".toc",
    ".lof",
    ".lot",
    ".fdb_latexmk",
    ".cut",
    ".synctex",
}
GENERATED_INPUTS = {".bbl", ".ind", ".gls", ".nls"}
FONT_SUFFIXES = {".otf", ".ttf", ".otc", ".ttc"}


def inside(path: Path, root: Path) -> bool:
    """Whether an absolute path is contained in an absolute root."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class BundleBuild:
    """Compiler input; font paths are relative to the document directory."""

    document: Path
    build_dir: Path
    timeout: int = 300
    font_paths: Tuple[str, ...] = ()

    @property
    def root(self) -> Path:
        return self.document.parent

    @property
    def pdf(self) -> Path:
        return self.build_dir / self.document.with_suffix(".pdf").name


@dataclass(frozen=True)
class BundleDependency:
    """A source mapped into the ZIP, bounded by its approved source root.

    Ordinarily source_root is the document directory. A backend can explicitly
    vendor an external package under a portable name using the package's root.
    The shared service still checks containment and prevents ZIP path escapes.
    """

    source: Path
    name: str
    source_root: Path


class BundleBackend(Protocol):
    """Strategy boundary for engine-specific build and dependency discovery."""

    suffix: str

    def compile(self, build: BundleBuild) -> None:
        """Build the PDF and dependency metadata, raising on failure."""
        ...

    def dependencies(self, build: BundleBuild) -> Iterable[BundleDependency]:
        """Read existing compiler metadata without changing files."""
        ...


class LatexBundleBackend:
    """Use latexmk recorder output and BibTeX auxiliary data."""

    suffix = ".tex"

    def __init__(self, engine: str, runner: CommandRunner):
        self.engine = engine
        self.runner = runner

    def compile(self, build: BundleBuild) -> None:
        mode = {"xelatex": "-xelatex", "lualatex": "-lualatex"}.get(self.engine, "-pdf")
        build.build_dir.mkdir(parents=True, exist_ok=True)
        result = self.runner.run(
            [
                "latexmk",
                mode,
                "-recorder",
                "-no-shell-escape",
                "-halt-on-error",
                "-interaction=nonstopmode",
                "-outdir=" + str(build.build_dir),
                build.document.name,
            ],
            cwd=build.root,
            timeout=build.timeout,
        )
        if result.returncode:
            raise ValueError(
                "Bundle compilation failed:\n" + (result.stdout + result.stderr)[-4000:]
            )
        log = build.build_dir / build.document.with_suffix(".log").name
        if log.is_file() and re.search(
            r"There were undefined (?:references|citations)|(?:Citation|Reference)[^\n]*undefined",
            log.read_text(errors="replace"),
        ):
            raise ValueError(
                "Bundle compilation has unresolved citations or references."
            )
        if not build.pdf.is_file():
            raise ValueError(
                "Bundle compilation reported success but PDF was not produced."
            )

    def dependencies(self, build: BundleBuild) -> Iterable[BundleDependency]:
        recorder = build.build_dir / build.document.with_suffix(".fls").name
        if not recorder.is_file():
            raise ValueError(
                f"No TeX recorder file: {recorder}. Build first, or supply --build-dir."
            )
        pwd = build.root
        for line in recorder.read_text(errors="replace").splitlines():
            if line.startswith("PWD "):
                pwd = Path(line[4:].strip()).resolve()
            elif line.startswith("INPUT "):
                raw = Path(line[6:].strip().strip('"'))
                lexical = Path(os.path.abspath(pwd / raw))
                path = lexical.resolve()
                if not inside(lexical, build.root):
                    if not raw.is_absolute():
                        raise ValueError(
                            f"Dependency outside the document directory: {raw}"
                        )
                    continue  # The receiving environment supplies system TeX files.
                if path == build.pdf.resolve():
                    continue
                if path.suffix in TEX_JUNK_SUFFIXES or path.name.endswith(
                    (".synctex.gz", ".run.xml")
                ):
                    continue
                generated = (
                    path.parent == build.build_dir and path.suffix in GENERATED_INPUTS
                )
                name = (
                    path.name
                    if generated
                    else lexical.relative_to(build.root).as_posix()
                )
                yield BundleDependency(lexical, name, build.root)
        # BibTeX input/style dependencies are not necessarily present in .fls.
        aux = build.build_dir / build.document.with_suffix(".aux").name
        if aux.is_file():
            data = aux.read_text(errors="replace")
            for command, suffix in [("bibdata", ".bib"), ("bibstyle", ".bst")]:
                for group in re.findall(r"\\" + command + r"\{([^}]+)\}", data):
                    for value in group.split(","):
                        raw = Path(value.strip())
                        if not raw.suffix:
                            raw = raw.with_suffix(suffix)
                        candidate = build.root / raw
                        if candidate.is_file() or suffix == ".bib":
                            yield BundleDependency(
                                candidate, raw.as_posix(), build.root
                            )
            if r"\bibdata" in data:
                bbl = build.build_dir / build.document.with_suffix(".bbl").name
                yield BundleDependency(bbl, bbl.name, build.root)

        # Biber reports bibliography sources in XML, rather than \bibdata in .aux.
        bcf = build.build_dir / build.document.with_suffix(".bcf").name
        if bcf.is_file():
            try:
                tree = ElementTree.parse(bcf)
            except ElementTree.ParseError as error:
                raise ValueError(f"Invalid Biber dependency metadata: {bcf}") from error
            for node in tree.iter():
                if node.tag.rsplit("}", 1)[-1] == "datasource" and node.text:
                    raw = Path(node.text.strip())
                    yield BundleDependency(build.root / raw, raw.as_posix(), build.root)
            bbl = build.build_dir / build.document.with_suffix(".bbl").name
            yield BundleDependency(bbl, bbl.name, build.root)


class TypstBundleBackend:
    """Use native JSON dependency reporting (Typst 0.14+) without parsing Typst."""

    suffix = ".typ"

    def __init__(self, runner: CommandRunner):
        self.runner = runner

    @staticmethod
    def recorder(build: BundleBuild) -> Path:
        return build.build_dir / (build.document.stem + ".typst-deps.json")

    def compile(self, build: BundleBuild) -> None:
        build.build_dir.mkdir(parents=True, exist_ok=True)
        command = [
            "typst",
            "compile",
            "--root",
            str(build.root),
            "--deps",
            str(self.recorder(build)),
            "--deps-format",
            "json",
            "--package-path",
            str(build.root / TYPST_PACKAGES),
        ]
        for name in build.font_paths:
            command.extend(["--font-path", str(build.root / name)])
        command.extend([build.document.name, str(build.pdf)])
        result = self.runner.run(command, cwd=build.root, timeout=build.timeout)
        if result.returncode:
            details = (result.stdout + result.stderr)[-4000:]
            raise ValueError(
                "Typst bundle compilation failed (requires Typst 0.14+):\n" + details
            )
        if not build.pdf.is_file() or not self.recorder(build).is_file():
            raise ValueError(
                "Typst compilation did not produce PDF and dependency metadata."
            )

    def dependencies(self, build: BundleBuild) -> Iterable[BundleDependency]:
        recorder = self.recorder(build)
        if not recorder.is_file():
            raise ValueError(
                f"No Typst dependency file: {recorder}. Build first, or supply --build-dir."
            )
        try:
            data = json.loads(recorder.read_text())
        except (ValueError, UnicodeError) as error:
            raise ValueError(
                f"Invalid Typst dependency metadata: {recorder}"
            ) from error
        inputs = data.get("inputs") if isinstance(data, dict) else None
        if not isinstance(inputs, list) or any(
            not isinstance(p, str) or not p for p in inputs
        ):
            raise ValueError(
                "Typst dependency metadata must contain an inputs list of paths."
            )
        packages = set()
        for value in inputs:
            # Native paths are relative to the compiler's cwd, not the JSON file.
            source = Path(os.path.abspath(build.root / value))
            if inside(source, build.root):
                yield BundleDependency(
                    source, source.relative_to(build.root).as_posix(), build.root
                )
                continue
            package_root = self._package_root(source)
            if package_root is None:
                raise ValueError(
                    f"Typst dependency outside the document directory is not a package: {source}"
                )
            namespace = package_root.parent.parent.name
            prefix = f"{TYPST_PACKAGES}/{namespace}/{package_root.parent.name}/{package_root.name}"
            yield BundleDependency(
                source,
                f"{prefix}/{source.relative_to(package_root).as_posix()}",
                package_root,
            )
            if package_root not in packages:
                packages.add(package_root)
                for path in sorted(package_root.iterdir()):
                    if path.is_file() and (
                        path.name == "typst.toml"
                        or path.name.lower().startswith(
                            ("license", "licence", "copying")
                        )
                    ):
                        yield BundleDependency(
                            path, f"{prefix}/{path.name}", package_root
                        )
        # Typst's dependency report does not list font files searched via --font-path.
        for name in build.font_paths:
            directory = build.root / name
            if not directory.is_dir():
                raise ValueError(f"Missing Typst font directory: {name}")
            for path in sorted(directory.rglob("*")):
                if path.is_file() and path.suffix.lower() in FONT_SUFFIXES:
                    yield BundleDependency(
                        path, path.relative_to(build.root).as_posix(), build.root
                    )

    @staticmethod
    def _package_root(source: Path) -> Optional[Path]:
        """Recognize a versioned package using its manifest and directory layout."""
        for parent in source.parents:
            manifest = parent / "typst.toml"
            if not manifest.is_file():
                continue
            try:
                data = tomllib.loads(manifest.read_text())
                package = data.get("package", {})
                if (
                    isinstance(package, dict)
                    and package.get("name") == parent.parent.name
                    and package.get("version") == parent.name
                    and re.fullmatch(r"[a-zA-Z0-9_-]+", parent.parent.parent.name)
                ):
                    return parent
            except (ValueError, UnicodeError):
                continue
        return None


def default_bundle_backends(runner: CommandRunner) -> Mapping[str, BundleBackend]:
    """Create the default strategy registry with one subprocess boundary."""
    backends: dict[str, BundleBackend] = {
        engine: LatexBundleBackend(engine, runner) for engine in LATEX_ENGINES
    }
    backends["typst"] = TypstBundleBackend(runner)
    return backends
