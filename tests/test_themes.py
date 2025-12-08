"""
Tests for theme installation module
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

from article_cli.themes import (
    ThemeInstaller,
    DEFAULT_THEME_SOURCES,
    get_available_themes,
    get_theme_info,
)


class TestThemeInstaller:
    """Tests for ThemeInstaller class"""

    def test_init_default_directory(self):
        """Test default themes directory is current directory"""
        installer = ThemeInstaller()
        assert installer.themes_dir == Path(".")

    def test_init_custom_directory(self):
        """Test custom themes directory"""
        custom_dir = Path("/custom/themes")
        installer = ThemeInstaller(themes_dir=custom_dir)
        assert installer.themes_dir == custom_dir

    def test_init_custom_sources(self):
        """Test custom theme sources"""
        custom_sources = {
            "custom-theme": {
                "url": "https://example.com/theme.zip",
                "description": "Custom theme",
            }
        }
        installer = ThemeInstaller(sources=custom_sources)
        assert "custom-theme" in installer.sources
        assert "numpex" not in installer.sources

    def test_init_default_sources(self):
        """Test default sources are used when none specified"""
        installer = ThemeInstaller()
        assert installer.sources == DEFAULT_THEME_SOURCES

    def test_list_available(self):
        """Test listing available themes"""
        installer = ThemeInstaller()
        available = installer.list_available()
        assert len(available) > 0
        assert any(t["name"] == "numpex" for t in available)

    def test_list_available_custom_sources(self):
        """Test listing available themes with custom sources"""
        custom_sources = {
            "theme1": {"url": "url1", "description": "Theme 1"},
            "theme2": {"url": "url2", "description": "Theme 2"},
        }
        installer = ThemeInstaller(sources=custom_sources)
        available = installer.list_available()
        assert len(available) == 2
        names = [t["name"] for t in available]
        assert "theme1" in names
        assert "theme2" in names

    def test_list_installed_empty(self):
        """Test listing installed themes when none are installed"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            installer = ThemeInstaller(themes_dir=Path(tmp_dir))
            installed = installer.list_installed()
            assert installed == []

    def test_list_installed_with_theme(self):
        """Test listing installed themes when theme is present"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create theme file
            (tmp_path / "beamerthemenumpex.sty").write_text("% theme")

            installer = ThemeInstaller(themes_dir=tmp_path)
            installed = installer.list_installed()

            assert len(installed) == 1
            assert installed[0]["name"] == "numpex"

    def test_install_theme_unknown(self):
        """Test installing unknown theme returns error"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            installer = ThemeInstaller(themes_dir=Path(tmp_dir))
            result = installer.install_theme("nonexistent-theme")
            assert result is False

    def test_install_theme_no_url(self):
        """Test installing theme with no URL configured"""
        custom_sources = {"broken-theme": {"description": "No URL"}}
        with tempfile.TemporaryDirectory() as tmp_dir:
            installer = ThemeInstaller(themes_dir=Path(tmp_dir), sources=custom_sources)
            result = installer.install_theme("broken-theme")
            assert result is False

    def test_install_theme_already_installed(self):
        """Test installing theme that's already installed (no force)"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create existing theme file
            (tmp_path / "beamerthemenumpex.sty").write_text("% existing theme")

            installer = ThemeInstaller(themes_dir=tmp_path)
            result = installer.install_theme("numpex", force=False)

            # Should return True (already installed)
            assert result is True
            # File should be unchanged
            assert (
                tmp_path / "beamerthemenumpex.sty"
            ).read_text() == "% existing theme"

    @patch.object(ThemeInstaller, "_download_and_extract_theme")
    def test_install_theme_success(self, mock_download):
        """Test successful theme installation"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            installer = ThemeInstaller(themes_dir=Path(tmp_dir))

            result = installer.install_theme("numpex", force=True)

            mock_download.assert_called_once()
            assert result is True

    @patch.object(ThemeInstaller, "_download_and_extract_theme")
    def test_install_theme_download_failure(self, mock_download):
        """Test theme installation with download failure"""
        mock_download.side_effect = RuntimeError("Network error")

        with tempfile.TemporaryDirectory() as tmp_dir:
            installer = ThemeInstaller(themes_dir=Path(tmp_dir))
            result = installer.install_theme("numpex", force=True)

            assert result is False

    @patch.object(ThemeInstaller, "_download_and_extract_theme")
    def test_install_from_url(self, mock_download):
        """Test installing theme from custom URL"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            installer = ThemeInstaller(themes_dir=Path(tmp_dir))

            result = installer.install_from_url(
                name="custom", url="https://example.com/theme.zip"
            )

            mock_download.assert_called_once()
            assert result is True

    def test_extract_theme_files_sty_only(self):
        """Test extracting only .sty files from archive"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create test zip with various files
            zip_path = tmp_path / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("repo-main/beamerthemetest.sty", "% style")
                zf.writestr("repo-main/README.md", "# Readme")
                zf.writestr("repo-main/other.txt", "other")

            output_dir = tmp_path / "output"
            output_dir.mkdir()

            installer = ThemeInstaller(themes_dir=output_dir)
            installer._extract_theme_files(zip_path, [], [])

            # Only .sty file should be extracted
            assert (output_dir / "beamerthemetest.sty").exists()
            assert not (output_dir / "README.md").exists()
            assert not (output_dir / "other.txt").exists()

    def test_extract_theme_files_specific_files(self):
        """Test extracting specific files from archive"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create test zip with theme files
            zip_path = tmp_path / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("repo-main/beamerthemenumpex.sty", "% main")
                zf.writestr("repo-main/beamercolorthemenumpex.sty", "% color")
                zf.writestr("repo-main/other.sty", "% other")

            output_dir = tmp_path / "output"
            output_dir.mkdir()

            installer = ThemeInstaller(themes_dir=output_dir)
            installer._extract_theme_files(
                zip_path, ["beamerthemenumpex.sty", "beamercolorthemenumpex.sty"], []
            )

            # Only specified files should be extracted
            assert (output_dir / "beamerthemenumpex.sty").exists()
            assert (output_dir / "beamercolorthemenumpex.sty").exists()
            assert not (output_dir / "other.sty").exists()

    def test_extract_theme_files_with_directories(self):
        """Test extracting directories from archive"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create test zip with images directory
            zip_path = tmp_path / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("repo-main/beamerthemenumpex.sty", "% main")
                zf.writestr("repo-main/images/logo.png", "PNG data")
                zf.writestr("repo-main/images/background.png", "PNG data")
                zf.writestr("repo-main/other/file.txt", "other")

            output_dir = tmp_path / "output"
            output_dir.mkdir()

            installer = ThemeInstaller(themes_dir=output_dir)
            installer._extract_theme_files(
                zip_path, ["beamerthemenumpex.sty"], ["images"]
            )

            # Theme file and images should be extracted
            assert (output_dir / "beamerthemenumpex.sty").exists()
            assert (output_dir / "images" / "logo.png").exists()
            assert (output_dir / "images" / "background.png").exists()
            # Other directory should not be extracted
            assert not (output_dir / "other").exists()

    def test_extract_theme_files_bad_zip(self):
        """Test extracting from invalid zip file"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create invalid zip
            zip_path = tmp_path / "bad.zip"
            zip_path.write_text("not a zip file")

            output_dir = tmp_path / "output"
            output_dir.mkdir()

            installer = ThemeInstaller(themes_dir=output_dir)

            with pytest.raises(RuntimeError, match="Invalid or corrupted zip file"):
                installer._extract_theme_files(zip_path, [], [])


class TestDefaultThemeSources:
    """Tests for default theme sources"""

    def test_numpex_theme_in_defaults(self):
        """Test numpex theme is in default sources"""
        assert "numpex" in DEFAULT_THEME_SOURCES

    def test_numpex_theme_has_url(self):
        """Test numpex theme has valid URL"""
        numpex = DEFAULT_THEME_SOURCES["numpex"]
        assert "url" in numpex
        assert numpex["url"].startswith("https://")

    def test_numpex_theme_has_files(self):
        """Test numpex theme specifies required files"""
        numpex = DEFAULT_THEME_SOURCES["numpex"]
        assert "files" in numpex
        files = numpex["files"]
        assert "beamerthemenumpex.sty" in files
        assert "beamercolorthemenumpex.sty" in files
        assert "beamerfontthemenumpex.sty" in files

    def test_numpex_theme_has_directories(self):
        """Test numpex theme specifies directories"""
        numpex = DEFAULT_THEME_SOURCES["numpex"]
        assert "directories" in numpex
        assert "images" in numpex["directories"]

    def test_numpex_theme_requires_fonts(self):
        """Test numpex theme indicates font requirement"""
        numpex = DEFAULT_THEME_SOURCES["numpex"]
        assert numpex.get("requires_fonts") is True

    def test_numpex_theme_engine(self):
        """Test numpex theme specifies xelatex engine"""
        numpex = DEFAULT_THEME_SOURCES["numpex"]
        assert numpex.get("engine") == "xelatex"


class TestHelperFunctions:
    """Tests for module-level helper functions"""

    def test_get_available_themes(self):
        """Test get_available_themes returns copy of defaults"""
        themes = get_available_themes()
        assert themes == DEFAULT_THEME_SOURCES
        # Should be a copy, not the original
        themes["new"] = {}
        assert "new" not in DEFAULT_THEME_SOURCES

    def test_get_theme_info_known(self):
        """Test get_theme_info for known theme"""
        info = get_theme_info("numpex")
        assert info is not None
        assert "url" in info

    def test_get_theme_info_unknown(self):
        """Test get_theme_info for unknown theme"""
        info = get_theme_info("nonexistent")
        assert info is None


class TestThemeInstallerDownload:
    """Tests for download functionality"""

    @patch("article_cli.themes.urlopen")
    def test_download_file_success(self, mock_urlopen):
        """Test successful file download"""
        # Mock response
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "100"}
        mock_response.read.side_effect = [b"x" * 100, b""]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dest = tmp_path / "downloaded.zip"

            installer = ThemeInstaller()
            installer._download_file("https://example.com/file.zip", dest)

            assert dest.exists()
            assert dest.read_bytes() == b"x" * 100

    @patch("article_cli.themes.urlopen")
    def test_download_file_http_error(self, mock_urlopen):
        """Test download with HTTP error"""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 404, "Not Found", {}, None
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dest = tmp_path / "downloaded.zip"

            installer = ThemeInstaller()

            with pytest.raises(RuntimeError, match="HTTP error 404"):
                installer._download_file("https://example.com/file.zip", dest)

    @patch("article_cli.themes.urlopen")
    def test_download_file_url_error(self, mock_urlopen):
        """Test download with URL error"""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dest = tmp_path / "downloaded.zip"

            installer = ThemeInstaller()

            with pytest.raises(RuntimeError, match="URL error"):
                installer._download_file("https://example.com/file.zip", dest)

    @patch("article_cli.themes.urlopen")
    def test_download_file_timeout(self, mock_urlopen):
        """Test download with timeout"""
        mock_urlopen.side_effect = TimeoutError()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dest = tmp_path / "downloaded.zip"

            installer = ThemeInstaller()

            with pytest.raises(RuntimeError, match="Download timed out"):
                installer._download_file("https://example.com/file.zip", dest)
