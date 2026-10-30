"""Source selection, archive integrity, and isolated verification contracts."""

import hashlib
import json
import shutil
import subprocess
import zipfile

import pytest

from article_cli.cli import create_parser
from article_cli.commands.bundle import run
from article_cli.config import Config
from article_cli.services.bundle import BundleOptions, BundleService


@pytest.fixture
def project(tmp_path):
    """Recorder data resembles latexmk with a separate output directory."""
    sources = {
        "paper.tex": r"\documentclass{custom}\input{sections/body}\bibliography{refs}",
        "custom.cls": "custom class",
        "sections/body.tex": "body",
        "figures/plot.pdf": "figure",
        "refs.bib": "@article{key,title={Title}}",
        "custom.bst": "bibliography style",
        "build/paper.bbl": "formatted bibliography",
        "build/paper.aux": "\\bibdata{refs}\n\\bibstyle{custom}\n",
        "build/paper.pdf": "compiled main PDF",
        "build/paper.log": "successful compilation",
        ".git": "gitdir: /private/worktree",
        "local-only/agreement.pdf": "private agreement",
        ".env": "private credentials",
        "notes.md": "extra notes",
        "supplement.csv.gz": "compressed supplement",
    }
    for name, data in sources.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    inputs = [
        "paper.tex",
        "custom.cls",
        "sections/body.tex",
        "figures/plot.pdf",
        "build/paper.aux",
        "build/paper.bbl",
        "build/paper.log",
        "build/paper.pdf",
    ]
    (tmp_path / "build/paper.fls").write_text(
        f"PWD {tmp_path}\nINPUT /usr/share/texmf/article.cls\n"
        + "".join(f"INPUT {name}\n" for name in inputs)
    )
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        """
[tool.article-cli.documents]
main = "paper.tex"
[tool.article-cli.workflow]
output_dir = "build"
"""
    )
    return tmp_path, config_path


def service_for(project, policy="", **kwargs):
    root, config_path = project
    if policy:
        with config_path.open("a") as stream:
            stream.write("\n[tool.article-cli.bundle]\n" + policy)
    return BundleService(Config(config_path, quiet=True), cwd=root, **kwargs)


def test_archive_contains_dependencies_and_portable_manifest(project):
    service = service_for(project)
    plan = service.plan(BundleOptions(no_build=True))
    expected = {
        "paper.tex",
        "custom.cls",
        "sections/body.tex",
        "figures/plot.pdf",
        "paper.bbl",
        "refs.bib",
        "custom.bst",
    }
    assert set(plan.files) == expected
    archive = service.write(plan)
    original = archive.read_bytes()
    with zipfile.ZipFile(archive) as zipped:
        assert set(zipped.namelist()) == expected
        assert zipped.read("paper.bbl") == b"formatted bibliography"
    manifest = json.loads(archive.with_suffix(".manifest.json").read_text())
    assert manifest["document"] == "paper.tex"
    assert manifest["verified"] is False
    assert str(project[0]) not in json.dumps(manifest)
    assert manifest["archive_sha256"] == hashlib.sha256(original).hexdigest()
    with pytest.raises(ValueError, match="already exists"):
        service.write(plan)
    service.write(plan, force=True)
    assert archive.read_bytes() == original


def test_config_and_cli_patterns_extend_with_exclude_precedence(project):
    service = service_for(project, 'include = ["**/*"]\nexclude = ["notes.md"]\n')
    plan = service.plan(
        BundleOptions(
            no_build=True, exclude=("pyproject.toml",), include=("supplement.csv.gz",)
        )
    )
    assert "supplement.csv.gz" in plan.files
    assert (
        not {
            ".git",
            ".env",
            "local-only/agreement.pdf",
            "notes.md",
            "pyproject.toml",
            "build/paper.pdf",
        }
        & plan.files.keys()
    )


def test_pdf_policy_can_be_overridden(project):
    service = service_for(project, "include_pdf = true\n")
    assert "paper.pdf" in service.plan(BundleOptions(no_build=True)).files
    assert (
        "paper.pdf"
        not in service.plan(BundleOptions(no_build=True, include_pdf=False)).files
    )


@pytest.mark.parametrize(
    "exclude", ["sections/**", "**/*.bib", "paper.bbl", "custom.cls"]
)
def test_required_dependency_exclusion_fails(project, exclude):
    with pytest.raises(ValueError, match="Required dependency excluded"):
        service_for(project).plan(BundleOptions(no_build=True, exclude=(exclude,)))


@pytest.mark.parametrize(
    "pattern", ["../secret", "/private/secret", "foo/../../secret", r"C:\secret"]
)
def test_unsafe_patterns_rejected(project, pattern):
    with pytest.raises(ValueError, match="must stay inside"):
        service_for(project).plan(BundleOptions(no_build=True, include=(pattern,)))


def test_missing_include_is_an_error(project):
    with pytest.raises(ValueError, match="matched no files"):
        service_for(project).plan(BundleOptions(no_build=True, include=("missing/**",)))


@pytest.mark.parametrize("name", ["build/paper.bbl", "refs.bib", "sections/body.tex"])
def test_missing_required_files_are_errors(project, name):
    (project[0] / name).unlink()
    with pytest.raises(ValueError, match="Missing"):
        service_for(project).plan(BundleOptions(no_build=True))


def test_symlink_escape_rejected(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret"
    outside.write_text("private")
    (project[0] / "linked").symlink_to(outside)
    with pytest.raises(ValueError, match="outside the document directory"):
        service_for(project).plan(BundleOptions(no_build=True, include=("linked",)))


def test_dry_run_writes_nothing(project, monkeypatch, capsys):
    monkeypatch.chdir(project[0])
    args = create_parser().parse_args(["bundle", "--dry-run"])
    assert run(args, Config(project[1], quiet=True)) == 0
    assert "paper.bbl" in capsys.readouterr().out
    assert not (project[0] / "dist").exists()


def test_missing_recorder_gives_actionable_error(project):
    (project[0] / "build/paper.fls").unlink()
    with pytest.raises(ValueError, match="Build first"):
        service_for(project).plan(BundleOptions(dry_run=True))


def test_root_build_directory_keeps_source_dependencies(project):
    root, config_path = project
    (root / "paper.fls").write_text(
        (root / "build/paper.fls").read_text().replace("build/paper", "paper")
    )
    shutil.copy(root / "build/paper.aux", root / "paper.aux")
    shutil.copy(root / "build/paper.bbl", root / "paper.bbl")
    plan = service_for(project).plan(BundleOptions(no_build=True, build_dir="."))
    assert {"custom.cls", "sections/body.tex", "refs.bib"} <= plan.files.keys()


def test_verification_failure_does_not_publish(project, monkeypatch):
    service = service_for(project)
    plan = service.plan(BundleOptions(no_build=True, verify=True))

    def fail(build):
        assert build.root != project[0]
        assert (build.root / "paper.bbl").is_file()
        assert not (build.root / "local-only").exists()
        raise ValueError("compilation failed")

    monkeypatch.setattr(service.backends["latexmk"], "compile", fail)
    with pytest.raises(ValueError, match="compilation failed"):
        service.write(plan)
    assert not plan.output.exists()
    assert not plan.output.with_suffix(".manifest.json").exists()


def test_compiler_failure_and_undefined_citations(project):
    class Runner:
        result = subprocess.CompletedProcess([], 1, "broken source", "")

        def run(self, command, **kwargs):
            assert "-no-shell-escape" in command
            assert "-recorder" in command
            return self.result

    runner = Runner()
    service = service_for(project, runner=runner)
    with pytest.raises(ValueError, match="broken source"):
        service.plan(BundleOptions())
    runner.result = subprocess.CompletedProcess([], 0, "", "")
    (project[0] / "build/paper.log").write_text("There were undefined references.")
    with pytest.raises(ValueError, match="unresolved citations"):
        service.plan(BundleOptions())


def test_clean_verification_with_real_latexmk(tmp_path):
    if not shutil.which("latexmk") or not shutil.which("pdflatex"):
        pytest.skip("LaTeX tools are not installed")
    (tmp_path / "paper.tex").write_text(
        r"\documentclass{article}\begin{document}Hello\input{body}\end{document}"
    )
    (tmp_path / "body.tex").write_text("World")
    config = tmp_path / "bundle.toml"
    config.write_text('[documents]\nmain="paper.tex"\n')
    service = BundleService(Config(config, quiet=True), cwd=tmp_path)
    plan = service.plan(BundleOptions(verify=True))
    output = service.write(plan)
    with zipfile.ZipFile(output) as zipped:
        assert set(zipped.namelist()) == {"paper.tex", "body.tex"}
    assert (
        json.loads(output.with_suffix(".manifest.json").read_text())["verified"] is True
    )


def test_real_biblatex_bundle_carries_biber_inputs(tmp_path):
    if not all(shutil.which(tool) for tool in ("latexmk", "pdflatex", "biber")):
        pytest.skip("LaTeX and Biber are required")
    (tmp_path / "paper.tex").write_text(
        r"""\documentclass{article}
\usepackage{biblatex}
\addbibresource{refs.bib}
\begin{document}See \cite{test}.\printbibliography\end{document}
"""
    )
    (tmp_path / "refs.bib").write_text(
        "@article{test,title={Testing},author={Doe, Jane},year={2026},journal={Tests}}"
    )
    config = tmp_path / "config.toml"
    config.write_text('[documents]\nmain="paper.tex"\n')
    service = BundleService(Config(config, quiet=True), cwd=tmp_path)
    plan = service.plan(BundleOptions(verify=True))
    output = service.write(plan)
    with zipfile.ZipFile(output) as archive:
        assert {"paper.tex", "refs.bib", "paper.bbl"} <= set(archive.namelist())
        assert not any(
            name.endswith((".bcf", ".run.xml")) for name in archive.namelist()
        )


@pytest.mark.parametrize("suffix", [".tex", ".typ"])
@pytest.mark.parametrize("include_pdf", [False, True])
def test_broad_includes_respect_main_pdf_policy(tmp_path, suffix, include_pdf):
    """Old PDFs and build-path aliases must not override main-PDF policy."""
    (tmp_path / "paper").with_suffix(suffix).write_text("Paper")
    (tmp_path / "paper.pdf").write_text("stale PDF from an earlier build")
    build = tmp_path / "build"
    build.mkdir()
    (build / "paper.pdf").write_text("current main PDF")
    (tmp_path / "figure.pdf").write_text("required figure PDF")
    if suffix == ".tex":
        (build / "paper.fls").write_text(
            f"PWD {tmp_path}\nINPUT paper.tex\nINPUT figure.pdf\n"
        )
    else:
        (build / "paper.typst-deps.json").write_text(
            json.dumps({"inputs": ["paper.typ", "figure.pdf"]})
        )
    config = tmp_path / "config.toml"
    config.write_text(
        f'[documents]\nmain="paper{suffix}"\n'
        '[workflow]\noutput_dir="build"\n'
        '[bundle]\ninclude=["**/*"]\n'
    )
    service = BundleService(Config(config, quiet=True), cwd=tmp_path)
    plan = service.plan(BundleOptions(no_build=True, include_pdf=include_pdf))
    output = service.write(plan)
    with zipfile.ZipFile(output) as archive:
        pdfs = {name for name in archive.namelist() if name.endswith(".pdf")}
        assert pdfs == ({"figure.pdf", "paper.pdf"} if include_pdf else {"figure.pdf"})
        if include_pdf:
            assert archive.read("paper.pdf") == b"current main PDF"


def test_broad_includes_do_not_duplicate_generated_bibliography(project):
    plan = service_for(project).plan(BundleOptions(no_build=True, include=("**/*",)))
    assert {name for name in plan.files if name.endswith(".bbl")} == {"paper.bbl"}
