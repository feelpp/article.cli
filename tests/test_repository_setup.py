"""
Tests for article-cli repository setup module

Tests project type support including article, presentation, and poster templates.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from article_cli.repository_setup import RepositorySetup


class TestRepositorySetupProjectTypes:
    """Test cases for project type support in RepositorySetup"""

    def test_init_default_repo_path(self):
        """Test RepositorySetup uses current directory by default"""
        setup = RepositorySetup()
        assert setup.repo_path == Path.cwd()

    def test_init_custom_repo_path(self):
        """Test RepositorySetup with custom path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            assert setup.repo_path == Path(temp_dir)

    def test_detect_or_create_tex_file_article_default(self):
        """Test default tex filename for article type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._detect_or_create_tex_file(
                None, "Test Title", ["Author One"], False, "article", "", "169"
            )
            # Should create main.tex for articles
            assert result == "main.tex"
            assert (Path(temp_dir) / "main.tex").exists()

    def test_detect_or_create_tex_file_presentation_default(self):
        """Test default tex filename for presentation type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._detect_or_create_tex_file(
                None, "Test Title", ["Author One"], False, "presentation", "", "169"
            )
            # Should create presentation.tex for presentations
            assert result == "presentation.tex"
            assert (Path(temp_dir) / "presentation.tex").exists()

    def test_detect_or_create_tex_file_poster_default(self):
        """Test default tex filename for poster type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._detect_or_create_tex_file(
                None, "Test Title", ["Author One"], False, "poster", "", "169"
            )
            # Should create poster.tex for posters
            assert result == "poster.tex"
            assert (Path(temp_dir) / "poster.tex").exists()

    def test_detect_existing_tex_file(self):
        """Test detection of existing .tex file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create an existing tex file
            existing_tex = Path(temp_dir) / "existing.tex"
            existing_tex.write_text("\\documentclass{article}")

            setup = RepositorySetup(Path(temp_dir))
            result = setup._detect_or_create_tex_file(
                None, "Test Title", ["Author One"], False, "article", "", "169"
            )
            # Should detect the existing file
            assert result == "existing.tex"


class TestArticleTemplate:
    """Test cases for article template generation"""

    def test_get_article_template_content(self):
        """Test article template contains expected elements"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_article_template("Test Article", ["John Doe"])

            assert "\\documentclass" in template
            assert "article" in template
            assert "Test Article" in template
            assert "\\usepackage{amsmath" in template
            assert "\\maketitle" in template

    def test_get_article_template_multiple_authors(self):
        """Test article template with multiple authors"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_article_template(
                "Multi-Author Article", ["Alice Smith", "Bob Jones", "Carol White"]
            )

            # Template includes authors list
            assert "Alice Smith" in template or "Multi-Author Article" in template


class TestPresentationTemplate:
    """Test cases for presentation (Beamer) template generation"""

    def test_get_presentation_template_basic(self):
        """Test presentation template contains expected Beamer elements"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_presentation_template(
                "Test Presentation", ["Presenter One"], "", "169"
            )

            assert "\\documentclass" in template
            assert "beamer" in template
            assert "Test Presentation" in template
            assert "Presenter One" in template

    def test_get_presentation_template_with_theme(self):
        """Test presentation template with custom Beamer theme"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_presentation_template(
                "Themed Presentation", ["Speaker"], "metropolis", "169"
            )

            assert "metropolis" in template
            assert "\\usetheme{metropolis}" in template

    def test_get_presentation_template_aspect_ratio_169(self):
        """Test presentation template with 16:9 aspect ratio"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_presentation_template(
                "Wide Presentation", ["Speaker"], "", "169"
            )

            assert "aspectratio=169" in template

    def test_get_presentation_template_aspect_ratio_43(self):
        """Test presentation template with 4:3 aspect ratio"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_presentation_template(
                "Standard Presentation", ["Speaker"], "", "43"
            )

            assert "aspectratio=43" in template

    def test_get_presentation_template_aspect_ratio_1610(self):
        """Test presentation template with 16:10 aspect ratio"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_presentation_template(
                "16:10 Presentation", ["Speaker"], "", "1610"
            )

            assert "aspectratio=1610" in template


class TestPosterTemplate:
    """Test cases for poster (beamerposter or tikzposter) template generation"""

    def test_get_poster_template_basic(self):
        """Test poster template contains expected elements"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_poster_template(
                "Test Poster", ["Researcher One", "Researcher Two"]
            )

            assert "\\documentclass" in template
            # May use tikzposter or beamerposter
            assert "poster" in template.lower()
            assert "Test Poster" in template

    def test_get_poster_template_size_a0(self):
        """Test poster template uses A0 size by default"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            template = setup._get_poster_template("Poster", ["Author"])

            # Should have A0 paper size settings
            assert "a0" in template.lower()


class TestConfigGeneration:
    """Test cases for configuration file generation"""

    def test_create_pyproject_article_type(self):
        """Test pyproject.toml generation for article type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_pyproject(
                "test-project",
                "Test Article",
                ["Author"],
                "12345",
                False,
                "article",
                "",
                "169",
            )

            assert result is True
            pyproject_path = Path(temp_dir) / "pyproject.toml"
            assert pyproject_path.exists()

            content = pyproject_path.read_text()
            assert "[tool.article-cli.project]" in content
            assert 'type = "article"' in content

    def test_create_pyproject_presentation_type(self):
        """Test pyproject.toml generation for presentation type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_pyproject(
                "test-presentation",
                "Test Presentation",
                ["Speaker"],
                "12345",
                False,
                "presentation",
                "numpex",
                "169",
            )

            assert result is True
            pyproject_path = Path(temp_dir) / "pyproject.toml"
            content = pyproject_path.read_text()

            assert "[tool.article-cli.project]" in content
            assert 'type = "presentation"' in content
            assert "[tool.article-cli.presentation]" in content
            assert 'theme = "numpex"' in content
            assert 'aspect_ratio = "169"' in content
            # Presentations should default to xelatex
            assert 'engine = "xelatex"' in content

    def test_create_pyproject_poster_type(self):
        """Test pyproject.toml generation for poster type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_pyproject(
                "test-poster",
                "Test Poster",
                ["Researcher"],
                "12345",
                False,
                "poster",
                "",
                "169",
            )

            assert result is True
            pyproject_path = Path(temp_dir) / "pyproject.toml"
            content = pyproject_path.read_text()

            assert "[tool.article-cli.project]" in content
            assert 'type = "poster"' in content
            assert "[tool.article-cli.poster]" in content


class TestReadmeGeneration:
    """Test cases for README.md generation"""

    def test_create_readme_article_type(self):
        """Test README.md generation for article type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_readme(
                "test-article", "Test Article", ["Author"], "main.tex", False, "article"
            )

            assert result is True
            readme_path = Path(temp_dir) / "README.md"
            assert readme_path.exists()

            content = readme_path.read_text()
            assert "Test Article" in content
            assert "latexmk -pdf main.tex" in content
            assert "article" in content.lower()

    def test_create_readme_presentation_type(self):
        """Test README.md generation for presentation type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_readme(
                "test-presentation",
                "Test Presentation",
                ["Speaker"],
                "presentation.tex",
                False,
                "presentation",
            )

            assert result is True
            readme_path = Path(temp_dir) / "README.md"
            content = readme_path.read_text()

            assert "Test Presentation" in content
            assert "latexmk -xelatex presentation.tex" in content
            assert "presentation" in content.lower()

    def test_create_readme_poster_type(self):
        """Test README.md generation for poster type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_readme(
                "test-poster",
                "Test Poster",
                ["Researcher"],
                "poster.tex",
                False,
                "poster",
            )

            assert result is True
            readme_path = Path(temp_dir) / "README.md"
            content = readme_path.read_text()

            assert "Test Poster" in content
            assert "latexmk -xelatex poster.tex" in content
            assert "poster" in content.lower()


class TestVSCodeSettingsGeneration:
    """Test cases for VS Code settings generation"""

    def test_create_vscode_settings_article(self):
        """Test VS Code settings for article type (pdflatex)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vscode_dir = Path(temp_dir) / ".vscode"
            vscode_dir.mkdir()

            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_vscode_settings(False, "article")

            assert result is True
            settings_path = vscode_dir / "settings.json"
            assert settings_path.exists()

            content = settings_path.read_text()
            assert "latexmk-pdf" in content
            assert '"-pdf"' in content

    def test_create_vscode_settings_presentation(self):
        """Test VS Code settings for presentation type (xelatex)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vscode_dir = Path(temp_dir) / ".vscode"
            vscode_dir.mkdir()

            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_vscode_settings(False, "presentation")

            assert result is True
            settings_path = vscode_dir / "settings.json"
            content = settings_path.read_text()

            assert "latexmk-xelatex" in content
            assert '"-xelatex"' in content

    def test_create_vscode_settings_poster(self):
        """Test VS Code settings for poster type (xelatex)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vscode_dir = Path(temp_dir) / ".vscode"
            vscode_dir.mkdir()

            setup = RepositorySetup(Path(temp_dir))
            result = setup._create_vscode_settings(False, "poster")

            assert result is True
            settings_path = vscode_dir / "settings.json"
            content = settings_path.read_text()

            assert "latexmk-xelatex" in content
            assert '"-xelatex"' in content


class TestFullRepositoryInit:
    """Integration tests for full repository initialization"""

    def test_init_article_repository(self):
        """Test full article repository initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup.init_repository(
                title="Test Article",
                authors=["Author One", "Author Two"],
                group_id="12345",
                force=False,
                project_type="article",
            )

            assert result is True
            # Check all expected files exist
            assert (Path(temp_dir) / "main.tex").exists()
            assert (Path(temp_dir) / "pyproject.toml").exists()
            assert (Path(temp_dir) / "README.md").exists()
            assert (Path(temp_dir) / ".gitignore").exists()
            assert (Path(temp_dir) / ".vscode" / "settings.json").exists()
            assert (Path(temp_dir) / ".github" / "workflows").exists()

    def test_init_presentation_repository(self):
        """Test full presentation repository initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup.init_repository(
                title="Test Presentation",
                authors=["Speaker One"],
                group_id="12345",
                force=False,
                project_type="presentation",
                theme="metropolis",
                aspect_ratio="169",
            )

            assert result is True
            # Check presentation-specific files
            assert (Path(temp_dir) / "presentation.tex").exists()

            # Check pyproject.toml has presentation config
            pyproject = (Path(temp_dir) / "pyproject.toml").read_text()
            assert 'type = "presentation"' in pyproject
            assert "[tool.article-cli.presentation]" in pyproject

    def test_init_poster_repository(self):
        """Test full poster repository initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = RepositorySetup(Path(temp_dir))
            result = setup.init_repository(
                title="Test Poster",
                authors=["Researcher"],
                group_id="12345",
                force=False,
                project_type="poster",
            )

            assert result is True
            # Check poster-specific files
            assert (Path(temp_dir) / "poster.tex").exists()

            # Check pyproject.toml has poster config
            pyproject = (Path(temp_dir) / "pyproject.toml").read_text()
            assert 'type = "poster"' in pyproject
            assert "[tool.article-cli.poster]" in pyproject


class TestConfigProjectMethods:
    """Test cases for Config class project type methods"""

    def test_get_project_config_defaults(self):
        """Test getting project configuration with defaults"""
        from article_cli.config import Config

        config = Config()
        project_config = config.get_project_config()

        # Uses 'project_type' key, defaults to 'article'
        assert project_config["project_type"] == "article"

    def test_get_presentation_config_defaults(self):
        """Test getting presentation configuration with defaults"""
        from article_cli.config import Config

        config = Config()
        presentation_config = config.get_presentation_config()

        assert presentation_config["theme"] == ""
        assert presentation_config["aspect_ratio"] == "169"

    def test_get_poster_config_defaults(self):
        """Test getting poster configuration with defaults"""
        from article_cli.config import Config

        config = Config()
        poster_config = config.get_poster_config()

        assert poster_config["size"] == "a0"
        assert poster_config["orientation"] == "portrait"
