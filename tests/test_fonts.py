"""
Tests for font installation module
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import zipfile
import io

from article_cli.fonts import FontInstaller, DEFAULT_FONT_SOURCES


class TestFontInstaller:
    """Tests for FontInstaller class"""

    def test_init_default_values(self):
        """Test FontInstaller initialization with defaults"""
        installer = FontInstaller()

        assert installer.fonts_dir == Path("fonts")
        assert installer.sources == DEFAULT_FONT_SOURCES

    def test_init_custom_values(self):
        """Test FontInstaller initialization with custom values"""
        custom_dir = Path("custom_fonts")
        custom_sources = [{"name": "Test", "url": "http://example.com/test.zip"}]

        installer = FontInstaller(fonts_dir=custom_dir, sources=custom_sources)

        assert installer.fonts_dir == custom_dir
        assert installer.sources == custom_sources

    def test_list_installed_empty(self, tmp_path):
        """Test listing installed fonts when directory is empty"""
        installer = FontInstaller(fonts_dir=tmp_path / "fonts")
        installed = installer.list_installed()

        assert installed == []

    def test_list_installed_nonexistent(self, tmp_path):
        """Test listing installed fonts when directory doesn't exist"""
        installer = FontInstaller(fonts_dir=tmp_path / "nonexistent")
        installed = installer.list_installed()

        assert installed == []

    def test_list_installed_with_fonts(self, tmp_path):
        """Test listing installed fonts"""
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        # Create some font directories
        (fonts_dir / "Marianne").mkdir()
        (fonts_dir / "RobotoMono").mkdir()
        (fonts_dir / ".hidden").mkdir()  # Should be ignored

        installer = FontInstaller(fonts_dir=fonts_dir)
        installed = installer.list_installed()

        assert set(installed) == {"Marianne", "RobotoMono"}

    def test_get_font_files_empty(self, tmp_path):
        """Test getting font files from empty directory"""
        installer = FontInstaller(fonts_dir=tmp_path / "fonts")
        files = installer.get_font_files()

        assert files == []

    def test_get_font_files_with_fonts(self, tmp_path):
        """Test getting font files"""
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        # Create some font files
        font_dir = fonts_dir / "TestFont"
        font_dir.mkdir()
        (font_dir / "regular.ttf").touch()
        (font_dir / "bold.otf").touch()
        (font_dir / "readme.txt").touch()  # Should be ignored

        installer = FontInstaller(fonts_dir=fonts_dir)
        files = installer.get_font_files()

        assert len(files) == 2
        assert all(f.suffix in [".ttf", ".otf"] for f in files)

    def test_get_font_files_specific_font(self, tmp_path):
        """Test getting font files for specific font"""
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        # Create font directories
        font1 = fonts_dir / "Font1"
        font1.mkdir()
        (font1 / "font1.ttf").touch()

        font2 = fonts_dir / "Font2"
        font2.mkdir()
        (font2 / "font2.ttf").touch()

        installer = FontInstaller(fonts_dir=fonts_dir)

        # Get files for specific font
        files = installer.get_font_files("Font1")
        assert len(files) == 1
        assert files[0].name == "font1.ttf"

    @patch("article_cli.fonts.urlopen")
    def test_download_file_success(self, mock_urlopen, tmp_path):
        """Test successful file download"""
        # Create mock response
        mock_response = MagicMock()
        mock_response.headers.get.return_value = "1000"
        mock_response.read.side_effect = [b"test content", b""]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        installer = FontInstaller(fonts_dir=tmp_path / "fonts")
        dest = tmp_path / "test.zip"

        installer._download_file("http://example.com/test.zip", dest)

        assert dest.exists()
        assert dest.read_bytes() == b"test content"

    def test_extract_zip(self, tmp_path):
        """Test zip extraction"""
        # Create a test zip file
        zip_path = tmp_path / "test.zip"
        target_dir = tmp_path / "extracted"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("font.ttf", b"fake font content")
            zf.writestr("subfolder/another.otf", b"another font")
            zf.writestr("readme.txt", b"readme content")

        installer = FontInstaller(fonts_dir=tmp_path / "fonts")
        installer._extract_zip(zip_path, target_dir)

        assert (target_dir / "font.ttf").exists()
        assert (target_dir / "subfolder" / "another.otf").exists()
        assert (target_dir / "readme.txt").exists()

    def test_extract_zip_invalid(self, tmp_path):
        """Test extraction of invalid zip file"""
        # Create an invalid zip file
        zip_path = tmp_path / "invalid.zip"
        zip_path.write_text("not a zip file")

        installer = FontInstaller(fonts_dir=tmp_path / "fonts")
        target_dir = tmp_path / "extracted"

        with pytest.raises(RuntimeError, match="Invalid or corrupted zip file"):
            installer._extract_zip(zip_path, target_dir)

    def test_install_font_already_exists(self, tmp_path):
        """Test that install_font skips existing fonts"""
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        # Pre-create the font directory
        font_dir = fonts_dir / "TestFont"
        font_dir.mkdir()

        installer = FontInstaller(fonts_dir=fonts_dir)
        result = installer.install_font("TestFont", "http://example.com/test.zip")

        assert result is True  # Should return True (considered successful)

    @patch.object(FontInstaller, "_download_and_extract")
    def test_install_font_force(self, mock_download, tmp_path):
        """Test that install_font with force re-downloads"""
        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()

        # Pre-create the font directory
        font_dir = fonts_dir / "TestFont"
        font_dir.mkdir()

        installer = FontInstaller(fonts_dir=fonts_dir)
        result = installer.install_font(
            "TestFont", "http://example.com/test.zip", force=True
        )

        assert mock_download.called

    @patch.object(FontInstaller, "_download_and_extract")
    def test_install_all_success(self, mock_download, tmp_path):
        """Test installing all fonts"""
        fonts_dir = tmp_path / "fonts"
        sources = [
            {"name": "Font1", "url": "http://example.com/font1.zip"},
            {"name": "Font2", "url": "http://example.com/font2.zip"},
        ]

        installer = FontInstaller(fonts_dir=fonts_dir, sources=sources)
        result = installer.install_all()

        assert result is True
        assert mock_download.call_count == 2

    @patch.object(FontInstaller, "_download_and_extract")
    def test_install_all_skip_no_url(self, mock_download, tmp_path):
        """Test that fonts without URL are skipped"""
        fonts_dir = tmp_path / "fonts"
        sources = [
            {"name": "Font1", "url": ""},  # No URL
            {"name": "Font2", "url": "http://example.com/font2.zip"},
        ]

        installer = FontInstaller(fonts_dir=fonts_dir, sources=sources)
        result = installer.install_all()

        assert result is True
        assert mock_download.call_count == 1


class TestDefaultFontSources:
    """Tests for default font sources"""

    def test_default_sources_structure(self):
        """Test that default sources have required fields"""
        for source in DEFAULT_FONT_SOURCES:
            assert "name" in source
            assert "url" in source
            assert source["url"].startswith("http")

    def test_default_sources_include_marianne(self):
        """Test that Marianne font is included"""
        names = [s["name"] for s in DEFAULT_FONT_SOURCES]
        assert "Marianne" in names

    def test_default_sources_include_roboto_mono(self):
        """Test that Roboto Mono font is included"""
        names = [s["name"] for s in DEFAULT_FONT_SOURCES]
        assert "Roboto Mono" in names
