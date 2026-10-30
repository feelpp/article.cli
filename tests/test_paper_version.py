"""Git snapshot lifecycle and versioned documents with real compilers."""

import json
import shutil
import subprocess
import zipfile

import pytest

from article_cli.config import Config
from article_cli.git_hooks import render_gitinfo2_metadata
from article_cli.git_manager import GitManager
from article_cli.paper_version import (
    read_git_snapshot,
    refresh_typst_metadata,
    write_typst_snapshot,
)
from article_cli.services.bundle import BundleOptions, BundleService
from article_cli.services.gitinfo import GitInfoService, VersionOptions
from article_cli.services.release import ReleaseOptions, ReleaseService
from article_cli.typst_compiler import TypstCompiler


def git(root, *args):
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Version Test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "paper.typ").write_text(
        '#let git = json("gitHeadLocal.json")\nVersion: #git.description'
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.article-cli.documents]
main = "paper.typ"
[tool.article-cli.typst]
build_dir = "build"
"""
    )
    (tmp_path / "gitHeadLocal.json").write_text("{}")
    (tmp_path / "gitHeadLocal.gin").write_text("old metadata")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "Baseline")
    git(tmp_path, "tag", "v1")
    return tmp_path


def test_snapshot_tag_hash_branch_and_dirty_state(repo):
    clean = read_git_snapshot(repo)
    assert clean is not None and not clean.dirty
    assert clean.commit == git(repo, "rev-parse", "HEAD")
    assert clean.release == "v1"
    assert clean.description.startswith("v1-0-g")
    assert clean.branch == git(repo, "branch", "--show-current")
    assert clean.commit_date
    (repo / "paper.typ").write_text("Changed source")
    dirty = read_git_snapshot(repo)
    assert dirty.dirty and dirty.description.endswith("-*")
    assert "-*" in render_gitinfo2_metadata(repo)


def test_generated_metadata_does_not_contaminate_dirty_flag(repo):
    (repo / "gitHeadLocal.gin").write_text("refreshed metadata")
    snapshot = refresh_typst_metadata(repo)
    assert snapshot is not None and not snapshot.dirty
    first = (repo / "gitHeadLocal.json").read_bytes()
    assert refresh_typst_metadata(repo) == snapshot
    assert (repo / "gitHeadLocal.json").read_bytes() == first
    assert not GitManager(repo).dirty_files(ignore_gitinfo=True)
    assert "-*" not in render_gitinfo2_metadata(repo)


def test_detached_head_and_nested_document(repo):
    git(repo, "checkout", "--detach", "-q")
    directory = repo / "nested"
    directory.mkdir()
    snapshot = refresh_typst_metadata(directory)
    assert snapshot.branch == "detached"
    assert (directory / "gitHeadLocal.json").is_file()
    assert snapshot.commit == git(repo, "rev-parse", "HEAD")


def test_archive_snapshot_preserved_without_git(tmp_path):
    snapshot = tmp_path / "gitHeadLocal.json"
    snapshot.write_text('{"description":"v1"}')
    assert refresh_typst_metadata(tmp_path) is None
    assert snapshot.read_text() == '{"description":"v1"}'


def test_version_dry_run_does_not_write(repo):
    config = Config(repo / "pyproject.toml", quiet=True)
    before = (repo / "gitHeadLocal.json").read_bytes()
    assert GitInfoService(config, repo_root=repo).refresh(VersionOptions(dry_run=True))
    assert (repo / "gitHeadLocal.json").read_bytes() == before


def test_typst_snapshot_strings_are_safely_encoded(repo):
    from dataclasses import replace

    snapshot = replace(read_git_snapshot(repo), branch='a"quote\\backslash_é')
    path = write_typst_snapshot(snapshot, repo)
    assert json.loads(path.read_text())["branch"] == snapshot.branch


def test_typst_compile_refreshes_metadata(repo):
    class Compiler(TypstCompiler):
        def _compile_once(self, typ_path, output_dir, font_paths):
            assert (
                json.loads((typ_path.parent / "gitHeadLocal.json").read_text())[
                    "release"
                ]
                == "v1"
            )
            return True

    assert Compiler(Config(repo / "pyproject.toml", quiet=True)).compile(
        str(repo / "paper.typ")
    )


def test_version_compile_check_and_frozen_typst_bundle(repo):
    if not shutil.which("typst") or not shutil.which("pdftotext"):
        pytest.skip("Typst and pdftotext are required")
    config = Config(repo / "pyproject.toml", quiet=True)
    service = GitInfoService(config, repo_root=repo)
    assert service.refresh(
        VersionOptions(compile_pdf=True, check_pdf=True, checksum=True)
    )
    snapshot = json.loads((repo / "gitHeadLocal.json").read_text())
    assert snapshot["release"] == "v1" and not snapshot["dirty"]
    bundle = BundleService(config, cwd=repo)
    output = bundle.write(bundle.plan(BundleOptions(verify=True)))
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {"paper.typ", "gitHeadLocal.json"}
        assert json.loads(archive.read("gitHeadLocal.json")) == snapshot
    assert json.loads(output.with_suffix(".manifest.json").read_text())["verified"]


def test_typst_release_refreshes_version_after_tagging(repo):
    if not shutil.which("typst") or not shutil.which("pdftotext"):
        pytest.skip("Typst and pdftotext are required")
    config = Config(repo / "pyproject.toml", quiet=True)
    assert ReleaseService(config, repo_root=repo).release(ReleaseOptions(tag="v2"))
    snapshot = json.loads((repo / "gitHeadLocal.json").read_text())
    assert snapshot["release"] == "v2"
    assert snapshot["description"].startswith("v2-0-g")


def test_latex_local_gitinfo2_survives_archive_verification(repo):
    if not shutil.which("latexmk") or not shutil.which("pdftotext"):
        pytest.skip("LaTeX and pdftotext are required")
    (repo / "paper.tex").write_text(
        r"""\documentclass{article}
\usepackage[local]{gitinfo2}
\begin{document}
Version: \gitDescribe{} / \gitAbbrevHash{}
\end{document}
"""
    )
    config = Config(repo / "pyproject.toml", quiet=True)
    assert GitInfoService(config, repo_root=repo).refresh(
        VersionOptions(
            document="paper.tex",
            engine="pdflatex",
            compile_pdf=True,
            check_pdf=True,
            tag="v1",
        )
    )
    # Select the LaTeX engine rather than the configured Typst main document.
    latex_config = repo / "latex.toml"
    latex_config.write_text(
        '[documents]\nmain="paper.tex"\n[latex]\nbuild_dir="build"\n'
    )
    service = BundleService(Config(latex_config, quiet=True), cwd=repo)
    output = service.write(service.plan(BundleOptions(verify=True)))
    with zipfile.ZipFile(output) as archive:
        assert "gitHeadLocal.gin" in archive.namelist()
        assert all(not name.startswith(".git/") for name in archive.namelist())


def test_typst_presentation_stamp_keeps_page_count(tmp_path):
    if not shutil.which("typst") or not shutil.which("pdftotext"):
        pytest.skip("Typst and pdftotext are required")
    from article_cli.paper_version import GitSnapshot
    from article_cli.repository_setup import RepositorySetup

    text = RepositorySetup(tmp_path)._get_typst_presentation_template(
        "Title", ["Author"], ""
    )
    (tmp_path / "slides.typ").write_text(text)
    write_typst_snapshot(GitSnapshot(description="v1"), tmp_path)
    subprocess.run(
        ["typst", "compile", "slides.typ"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    result = subprocess.run(
        ["pdftotext", str(tmp_path / "slides.pdf"), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert result.count("\f") == 5
    assert result.count("Version: v1") == 5


@pytest.mark.parametrize("action", ["compile_pdf", "check_pdf", "checksum"])
def test_missing_document_fails_before_metadata_refresh(repo, action, capsys):
    (repo / "paper.typ").unlink()
    before = (repo / "gitHeadLocal.json").read_bytes()
    gin_before = (repo / "gitHeadLocal.gin").read_bytes()
    service = GitInfoService(
        Config(repo / "pyproject.toml", quiet=True), repo_root=repo
    )
    assert not service.refresh(VersionOptions(**{action: True}))
    assert (repo / "gitHeadLocal.json").read_bytes() == before
    assert (repo / "gitHeadLocal.gin").read_bytes() == gin_before
    assert str(repo) in capsys.readouterr().err
