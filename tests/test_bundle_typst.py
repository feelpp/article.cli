"""Typst parity and the engine strategy boundary for submission bundles."""

import json
import shutil
import subprocess
import zipfile

import pytest

from article_cli.cli import create_parser
from article_cli.commands.bundle import run
from article_cli.config import Config
from article_cli.services.bundle import BundleOptions, BundleService
from article_cli.services.bundle_backends import BundleDependency, TYPST_PACKAGES


@pytest.fixture
def typst_project(tmp_path):
    files = {
        "paper.typ": '#include "sections/body.typ"',
        "sections/body.typ": "Nested content",
        "figures/plot.svg": "<svg/>",
        "data/results.json": '{"value":42}',
        "refs.bib": "@article{test,title={Test}}",
        "style.csl": "custom bibliography style",
        "notes.md": "extra notes",
        ".env": "secret",
        "local-only/agreement.pdf": "private",
        "fonts/project.ttf": "font",
        "build/paper.pdf": "%PDF",
    }
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (tmp_path / "build/paper.typst-deps.json").write_text(
        json.dumps(
            {
                "inputs": [
                    "paper.typ",
                    "sections/body.typ",
                    "figures/plot.svg",
                    "data/results.json",
                    "refs.bib",
                    "style.csl",
                ],
                "outputs": ["build/paper.pdf"],
            }
        )
    )
    config = tmp_path / "pyproject.toml"
    config.write_text(
        """
[tool.article-cli.documents]
main = "paper.typ"
[tool.article-cli.typst]
build_dir = "build"
font_paths = ["fonts"]
[tool.article-cli.bundle]
include = ["notes.md"]
verify = false
"""
    )
    return tmp_path, config


def service_for(project, **kwargs):
    root, config = project
    return BundleService(Config(config, quiet=True), cwd=root, **kwargs)


def test_typst_dependency_archive_and_manifest(typst_project):
    service = service_for(typst_project)
    plan = service.plan(BundleOptions(no_build=True))
    assert plan.engine == "typst"
    assert set(plan.files) == {
        "paper.typ",
        "sections/body.typ",
        "figures/plot.svg",
        "data/results.json",
        "refs.bib",
        "style.csl",
        "fonts/project.ttf",
        "notes.md",
    }
    output = service.write(plan)
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == set(plan.files)
    metadata = json.loads(output.with_suffix(".manifest.json").read_text())
    assert metadata["engine"] == "typst"
    assert metadata["font_paths"] == ["fonts"]
    assert str(typst_project[0]) not in json.dumps(metadata)
    before = output.read_bytes()
    service.write(plan, force=True)
    assert output.read_bytes() == before


def test_typst_cli_dry_run_and_overrides(typst_project, monkeypatch, capsys):
    root, config = typst_project
    monkeypatch.chdir(root)
    args = create_parser().parse_args(
        ["bundle", "paper.typ", "--dry-run", "--exclude", "notes.md", "--include-pdf"]
    )
    assert args.document == "paper.typ"
    assert run(args, Config(config, quiet=True)) == 0
    output = capsys.readouterr().out
    assert "paper.pdf" in output
    assert "notes.md" not in output
    assert not (root / "dist").exists()


@pytest.mark.parametrize("excluded", ["sections/**", "**/*.bib", "data/**", "fonts/**"])
def test_typst_required_exclusions_fail(typst_project, excluded):
    with pytest.raises(ValueError, match="Required dependency excluded"):
        service_for(typst_project).plan(
            BundleOptions(no_build=True, exclude=(excluded,))
        )


def test_typst_broad_includes_keep_private_files_and_metadata_out(typst_project):
    plan = service_for(typst_project).plan(
        BundleOptions(no_build=True, include=("**/*",))
    )
    assert (
        not {
            ".env",
            "local-only/agreement.pdf",
            "build/paper.typst-deps.json",
            "build/paper.pdf",
        }
        & plan.files.keys()
    )


@pytest.mark.parametrize("metadata", ["not json", "{}", "[]", '{"inputs":[1]}'])
def test_typst_bad_dependency_data(typst_project, metadata):
    (typst_project[0] / "build/paper.typst-deps.json").write_text(metadata)
    with pytest.raises(ValueError, match="metadata"):
        service_for(typst_project).plan(BundleOptions(no_build=True))


def test_typst_missing_metadata_actionable(typst_project):
    (typst_project[0] / "build/paper.typst-deps.json").unlink()
    with pytest.raises(ValueError, match="Build first"):
        service_for(typst_project).plan(BundleOptions(dry_run=True))


def test_typst_missing_source_fails(typst_project):
    (typst_project[0] / "sections/body.typ").unlink()
    with pytest.raises(ValueError, match="Missing bundle dependency"):
        service_for(typst_project).plan(BundleOptions(no_build=True))


def test_typst_symlink_escape_fails(typst_project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("external") / "secret"
    outside.write_text("secret")
    path = typst_project[0] / "sections/body.typ"
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="outside the document directory"):
        service_for(typst_project).plan(BundleOptions(no_build=True))


def test_typst_external_file_not_silently_omitted(typst_project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("external") / "secret"
    outside.write_text("secret")
    (typst_project[0] / "build/paper.typst-deps.json").write_text(
        json.dumps({"inputs": [str(outside)]})
    )
    with pytest.raises(ValueError, match="not a package"):
        service_for(typst_project).plan(BundleOptions(no_build=True))


def test_typst_compiler_errors_do_not_publish(typst_project):
    class Runner:
        def run(self, command, **kwargs):
            assert command[:2] == ["typst", "compile"]
            assert "--deps-format" in command
            assert command[command.index("--font-path") + 1].endswith("/fonts")
            return subprocess.CompletedProcess(command, 1, "", "unknown label")

    with pytest.raises(ValueError, match="unknown label"):
        service_for(typst_project, runner=Runner()).plan(BundleOptions())
    assert not (typst_project[0] / "dist").exists()


def test_custom_backend_can_be_injected_without_inheritance(tmp_path):
    """The service depends on the protocol, not either concrete compiler."""
    document = tmp_path / "main.typ"
    document.write_text("Hello")
    config = tmp_path / "config.toml"
    config.write_text('[documents]\nmain="main.typ"\n')

    class Backend:
        suffix = ".typ"
        builds = []

        def compile(self, build):
            self.builds.append(build)

        def dependencies(self, build):
            return [BundleDependency(build.document, "main.typ", build.root)]

    backend = Backend()
    service = BundleService(
        Config(config, quiet=True), cwd=tmp_path, backends={"typst": backend}
    )
    plan = service.plan(BundleOptions(verify=True))
    service.write(plan)
    assert len(backend.builds) == 2
    assert backend.builds[0].root == tmp_path
    assert backend.builds[1].root != tmp_path
    assert backend.builds[1].font_paths == ()


def require_typst():
    if not shutil.which("typst"):
        pytest.skip("Typst is not installed")
    help_text = subprocess.run(
        ["typst", "compile", "--help"], capture_output=True, text=True, check=True
    ).stdout
    if "--deps-format" not in help_text:
        pytest.skip("Typst 0.14+ is required for native dependency reporting")


def test_real_typst_dynamic_dependencies_and_clean_verification(tmp_path):
    require_typst()
    (tmp_path / "sections").mkdir()
    (tmp_path / "sections/body.typ").write_text("Nested body")
    (tmp_path / "observations.log").write_text("Recorded observations")
    (tmp_path / "results.json").write_text('{"message":"Dynamic data"}')
    (tmp_path / "plot.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20"/></svg>'
    )
    (tmp_path / "refs.bib").write_text(
        "@article{test, title={Testing}, author={Doe, Jane}, year={2026}, journal={Tests}}"
    )
    (tmp_path / "main.typ").write_text(
        """
#include "sections/body.typ"
#let filename = "results" + ".json"
#json(filename).message
#read("observations.log")
#image("plot.svg")
See @test.
#bibliography("refs.bib")
"""
    )
    config = tmp_path / "config.toml"
    config.write_text('[documents]\nmain="main.typ"\n')
    service = BundleService(Config(config, quiet=True), cwd=tmp_path)
    plan = service.plan(BundleOptions(verify=True, include_pdf=True))
    output = service.write(plan)
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {
            "main.typ",
            "sections/body.typ",
            "results.json",
            "observations.log",
            "plot.svg",
            "refs.bib",
            "main.pdf",
        }
    assert json.loads(output.with_suffix(".manifest.json").read_text())["verified"]


@pytest.mark.parametrize("namespace", ["local", "preview"])
def test_real_typst_external_package_is_vendored_and_rebuilt(tmp_path, namespace):
    require_typst()
    project = tmp_path / "project"
    project.mkdir()
    package = tmp_path / f"packages/{namespace}/example/1.0.0"
    package.mkdir(parents=True)
    (package / "typst.toml").write_text(
        '[package]\nname="example"\nversion="1.0.0"\nentrypoint="lib.typ"\n'
    )
    (package / "lib.typ").write_text("#let greeting = [Vendored package]")
    (package / "LICENSE").write_text("Test package license")
    (project / "main.typ").write_text(
        f'#import "@{namespace}/example:1.0.0": greeting\n#greeting'
    )
    build = project / "build"
    build.mkdir()
    # Produce real dependency metadata using an external local package installation.
    subprocess.run(
        [
            "typst",
            "compile",
            "--root",
            str(project),
            "--package-path",
            str(tmp_path / "packages"),
            "--deps",
            str(build / "main.typst-deps.json"),
            "--deps-format",
            "json",
            "main.typ",
            str(build / "main.pdf"),
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    )
    config = project / "config.toml"
    config.write_text('[documents]\nmain="main.typ"\n[typst]\nbuild_dir="build"\n')
    service = BundleService(Config(config, quiet=True), cwd=project)
    plan = service.plan(BundleOptions(no_build=True, verify=True))
    prefix = f"{TYPST_PACKAGES}/{namespace}/example/1.0.0"
    assert {
        f"{prefix}/lib.typ",
        f"{prefix}/typst.toml",
        f"{prefix}/LICENSE",
    } <= plan.files.keys()
    output = service.write(plan)
    assert json.loads(output.with_suffix(".manifest.json").read_text())["verified"]


def test_verification_relocates_configured_fonts(typst_project, monkeypatch):
    service = service_for(typst_project)
    plan = service.plan(BundleOptions(no_build=True, verify=True))
    builds = []

    def compile(build):
        builds.append(build)
        assert build.root != typst_project[0]
        assert build.font_paths == ("fonts",)
        assert (build.root / "fonts/project.ttf").read_text() == "font"

    monkeypatch.setattr(service.backends["typst"], "compile", compile)
    service.write(plan)
    assert len(builds) == 1
