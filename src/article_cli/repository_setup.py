"""
Repository setup module for article-cli

Provides functionality to initialize LaTeX article repositories with:
- GitHub Actions workflows
- Python project configuration
- README documentation
- Git hooks and configuration
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .zotero import print_error, print_info, print_success


class RepositorySetup:
    """Handles complete repository initialization for LaTeX article projects"""

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize repository setup

        Args:
            repo_path: Path to repository (defaults to current directory)
        """
        self.repo_path = repo_path or Path.cwd()

    def init_repository(
        self,
        title: str,
        authors: List[str],
        group_id: str = "4678293",
        force: bool = False,
        main_tex_file: Optional[str] = None,
    ) -> bool:
        """
        Initialize a complete LaTeX article repository

        Creates:
        - GitHub Actions workflow for automated PDF compilation
        - pyproject.toml with article-cli configuration
        - README.md with documentation
        - .gitignore with LaTeX-specific patterns
        - .vscode/settings.json with LaTeX Workshop configuration
        - LTeX dictionary files for spell checking
        - hooks/post-commit for gitinfo2 integration

        Args:
            title: Article title
            authors: List of author names
            group_id: Zotero group ID
            force: Overwrite existing files if True
            main_tex_file: Main .tex filename (auto-detected if None)

        Returns:
            True if successful, False otherwise
        """
        print_info(f"Initializing repository at: {self.repo_path}")

        # Detect or validate main .tex file
        tex_file = self._detect_tex_file(main_tex_file)
        if not tex_file:
            print_error("No main .tex file found or specified")
            return False

        project_name = self.repo_path.name
        print_info(f"Project name: {project_name}")
        print_info(f"Main tex file: {tex_file}")
        print_info(f"Article title: {title}")
        print_info(f"Authors: {', '.join(authors)}")

        try:
            # Create directory structure
            self._create_directories()

            # Create GitHub Actions workflows
            if not self._create_workflow(project_name, tex_file, force):
                return False

            # Create pyproject.toml
            if not self._create_pyproject(
                project_name, title, authors, group_id, force
            ):
                return False

            # Create README
            if not self._create_readme(project_name, title, authors, tex_file, force):
                return False

            # Create .gitignore if needed
            self._create_gitignore(force)

            # Create VS Code configuration
            self._create_vscode_settings(force)

            # Create git hooks directory and post-commit hook
            self._create_git_hooks(force)

            print_success("\n✅ Repository initialization complete!")
            print_info("\nNext steps:")
            print_info("  1. Review and edit pyproject.toml")
            print_info("  2. Add ZOTERO_API_KEY secret to GitHub repository")
            print_info("  3. Run: article-cli setup")
            print_info("  4. Run: article-cli update-bibtex")
            print_info("  5. Commit and push changes")

            return True

        except Exception as e:
            print_error(f"Failed to initialize repository: {e}")
            return False

    def _detect_tex_file(self, specified: Optional[str]) -> Optional[str]:
        """
        Detect main .tex file in repository

        Args:
            specified: User-specified filename (takes priority)

        Returns:
            Main .tex filename or None if not found
        """
        if specified:
            tex_path = self.repo_path / specified
            if tex_path.exists():
                return specified
            print_error(f"Specified .tex file not found: {specified}")
            return None

        # Auto-detect .tex files
        tex_files = list(self.repo_path.glob("*.tex"))

        if not tex_files:
            return None

        if len(tex_files) == 1:
            return tex_files[0].name

        # Multiple .tex files - prefer common patterns
        for pattern in ["main.tex", "article.tex", f"{self.repo_path.name}.tex"]:
            if (self.repo_path / pattern).exists():
                return pattern

        # Return first .tex file found
        print_info(
            f"Multiple .tex files found, using: {tex_files[0].name} "
            "(use --tex-file to specify different file)"
        )
        return tex_files[0].name

    def _create_directories(self) -> None:
        """Create necessary directory structure"""
        directories = [
            self.repo_path / ".github" / "workflows",
            self.repo_path / ".vscode",
            self.repo_path / "hooks",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print_info(f"Created directory: {directory.relative_to(self.repo_path)}")

    def _create_workflow(
        self, project_name: str, tex_file: str, force: bool
    ) -> bool:
        """
        Create GitHub Actions workflow file

        Args:
            project_name: Name of the project
            tex_file: Main .tex filename
            force: Overwrite if exists

        Returns:
            True if successful
        """
        workflow_path = self.repo_path / ".github" / "workflows" / "latex.yml"

        if workflow_path.exists() and not force:
            print_info(f"Workflow already exists: {workflow_path.name} (use --force to overwrite)")
            return True

        # Extract base name (without .tex extension)
        tex_base = tex_file.replace(".tex", "")

        workflow_content = self._get_workflow_template(project_name, tex_base)

        workflow_path.write_text(workflow_content)
        print_success(f"Created workflow: {workflow_path.relative_to(self.repo_path)}")
        return True

    def _get_workflow_template(self, project_name: str, tex_base: str) -> str:
        """
        Get GitHub Actions workflow template

        Args:
            project_name: Name of the project
            tex_base: Base name of .tex file (without extension)

        Returns:
            Workflow YAML content
        """
        return f'''name: Compile LaTeX and Release PDF

# This workflow uses article-cli for:
# - Git hooks setup (article-cli setup)
# - Bibliography updates from Zotero (article-cli update-bibtex)
# - LaTeX build file cleanup (article-cli clean)

on:
  push:
    tags:
      - 'v*'
    branches:
      - 'main'
  pull_request:
    branches:
      - 'main'

jobs:
  workflow-setup:
    name: Workflow Setup
    runs-on: ubuntu-24.04
    outputs:
      runner: ${{{{ steps.texlive_runner.outputs.runner }}}}
      prefix: ${{{{ steps.doc_prefix.outputs.prefix }}}}
      prefixwithref: ${{{{ steps.doc_prefix.outputs.prefixwithref }}}}
      pdf: ${{{{ steps.doc_prefix.outputs.pdf }}}}
      tex: ${{{{ steps.doc_prefix.outputs.tex }}}}
    steps:
      - name: Get TeXLive Runner
        id: texlive_runner
        run: |
          if ! [ -z "$GH_TOKEN" ]; then
            runners=$(gh api -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /orgs/feelpp/actions/runners)
            texlive=$(echo $runners | jq --arg label "self-texlive" '[.runners[] | any(.labels[]; .name == $label) and .status == "online"] | any')
            if [ "$texlive" = "false" ]; then
               echo "runner=ubuntu-latest" >> "$GITHUB_OUTPUT"
            else
                echo "runner=self-texlive" >> "$GITHUB_OUTPUT"
            fi
          else
            echo "runner=ubuntu-latest" >> "$GITHUB_OUTPUT"
          fi
        env:
          GH_TOKEN: ${{{{ secrets.TOKEN_RUNNER }}}}

      - name: Get Document Prefix
        id: doc_prefix
        run: |
          prefix=$(echo "${{{{ github.repository }}}}" | cut -d'/' -f2)
          echo "prefix=$prefix" >> "$GITHUB_OUTPUT"
          
          # Handle different event types for naming
          if [[ "${{{{ github.event_name }}}}" == "pull_request" ]]; then
            # For pull requests, use pr-NUMBER format
            prefixwithref=$(echo "$prefix")-pr-${{{{ github.event.number }}}}
          else
            # For tags and branches, use the ref name
            prefixwithref=$(echo "$prefix")-${{{{ github.ref_name }}}}
          fi
          
          echo "prefixwithref=$prefixwithref" >> "$GITHUB_OUTPUT"
          echo "pdf=$prefixwithref.pdf" >> "$GITHUB_OUTPUT"
          echo "tex={tex_base}.tex" >> "$GITHUB_OUTPUT"
      -
        name: Show Outputs
        run: |
          echo "runner=${{{{ steps.texlive_runner.outputs.runner }}}}"
          echo "prefix=${{{{ steps.doc_prefix.outputs.prefix }}}}"
          echo "prefixwithref=${{{{ steps.doc_prefix.outputs.prefixwithref }}}}"
          echo "pdf=${{{{ steps.doc_prefix.outputs.pdf }}}}"
          echo "tex=${{{{ steps.doc_prefix.outputs.tex }}}}"


  build_latex:
    needs: workflow-setup
    runs-on: ${{{{ needs.workflow-setup.outputs.runner }}}}
    name: Build LaTeX Artifact
    env:
      VERSION: ${{{{ github.ref_name }}}}
    steps:
      - name: Set up Git repository
        uses: actions/checkout@v4
        with:
          clean: true

      - name: Set up Python and uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
          enable-cache: false

      - name: Set up Python
        run: uv python install 3.11

      - name: Create virtual environment and install article-cli
        run: |
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## ⚡ Fast Python Setup with UV" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Setting up isolated Python environment..." >> $GITHUB_STEP_SUMMARY

          start_time=$(date +%s)
          uv venv .venv --python 3.11
          echo "VIRTUAL_ENV=${{PWD}}/.venv" >> $GITHUB_ENV
          echo "${{PWD}}/.venv/bin" >> $GITHUB_PATH
          uv pip install "article-cli>=1.1.0"
          end_time=$(date +%s)
          duration=$((end_time - start_time))

          echo "✅ **Environment Setup Complete**" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Tool**: UV (fast Python package installer)" >> $GITHUB_STEP_SUMMARY
          echo "- **Python**: 3.11 (isolated virtual environment)" >> $GITHUB_STEP_SUMMARY
          echo "- **Package**: article-cli>=1.1.0" >> $GITHUB_STEP_SUMMARY
          echo "- **Duration**: ${{duration}}s" >> $GITHUB_STEP_SUMMARY
          echo "- **Cache**: Enabled for faster subsequent runs" >> $GITHUB_STEP_SUMMARY

      - name: Install hooks and setup
        run: |
          article-cli setup
          
          # Add git status to summary
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 🔧 Git Setup" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Event**: ${{{{ github.event_name }}}}" >> $GITHUB_STEP_SUMMARY
          echo "- **Ref**: ${{{{ github.ref }}}}" >> $GITHUB_STEP_SUMMARY
          echo "- **SHA**: ${{{{ github.sha }}}}" >> $GITHUB_STEP_SUMMARY
          
          # For pull requests, stay on the current commit; for branches/tags, checkout the ref
          if [[ "${{{{ github.event_name }}}}" == "pull_request" ]]; then
            echo "- **Action**: Staying on PR merge commit" >> $GITHUB_STEP_SUMMARY
            echo "- **PDF Name**: ${{{{ needs.workflow-setup.outputs.pdf }}}} (pr-${{{{ github.event.number }}}} format)" >> $GITHUB_STEP_SUMMARY
            echo "Pull request detected - staying on current commit ${{{{ github.sha }}}}"
          else
            echo "- **Action**: Checking out ${{{{ github.ref }}}}" >> $GITHUB_STEP_SUMMARY
            echo "- **PDF Name**: ${{{{ needs.workflow-setup.outputs.pdf }}}} (ref-based format)" >> $GITHUB_STEP_SUMMARY
            echo "Checking out ${{{{ github.ref }}}}"
            git checkout ${{{{ github.ref }}}}
          fi

      - name: Show article-cli configuration
        run: |
          article-cli --version
          article-cli config show
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 🔧 Environment Configuration" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Python Environment:" >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
          echo "UV Version: $(uv --version)" >> $GITHUB_STEP_SUMMARY
          echo "Python Version: $(python --version)" >> $GITHUB_STEP_SUMMARY
          echo "Virtual Environment: $VIRTUAL_ENV" >> $GITHUB_STEP_SUMMARY
          echo "Article CLI: $(article-cli --version)" >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Configuration Details:" >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
          article-cli config show >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY

      - name: Update bibliography from Zotero
        run: |
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 📚 Bibliography Update" >> $GITHUB_STEP_SUMMARY
          echo "Updating bibliography from Zotero group using isolated virtual environment..." >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY

          if article-cli update-bibtex; then
            echo "✅ **Bibliography Updated Successfully**" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
            echo "- **Environment**: Isolated venv with uv" >> $GITHUB_STEP_SUMMARY
            echo "- **Source**: Zotero Group (configured in pyproject.toml)" >> $GITHUB_STEP_SUMMARY
            echo "- **Output**: references.bib" >> $GITHUB_STEP_SUMMARY
            echo "- **Backup**: references.bib.backup" >> $GITHUB_STEP_SUMMARY
            if [ -f references.bib ]; then
              entries=$(grep -c "^@" references.bib || echo "0")
              echo "- **Total entries**: $entries" >> $GITHUB_STEP_SUMMARY
            fi
          else
            echo "❌ **Bibliography Update Failed**" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
            echo "Please check Zotero API key and group permissions." >> $GITHUB_STEP_SUMMARY
            exit 1
          fi
        env:
          ZOTERO_API_KEY: ${{{{ secrets.ZOTERO_API_KEY }}}}

      - name: Compile LaTeX document
        uses: xu-cheng/latex-action@v3
        if: ${{{{ needs.workflow-setup.outputs.runner == 'ubuntu-latest' }}}}
        with:
          root_file: ${{{{ needs.workflow-setup.outputs.tex }}}}
          latexmk_shell_escape: true
          post_compile: "article-cli clean"

      - name: Generate compilation summary (Ubuntu)
        if: ${{{{ needs.workflow-setup.outputs.runner == 'ubuntu-latest' }}}}
        run: |
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 🔨 LaTeX Compilation (Ubuntu)" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Engine**: latexmk with shell-escape" >> $GITHUB_STEP_SUMMARY
          echo "- **Runner**: ubuntu-latest (xu-cheng/latex-action@v3)" >> $GITHUB_STEP_SUMMARY
          echo "- **Source**: \`${{{{ needs.workflow-setup.outputs.tex }}}}\`" >> $GITHUB_STEP_SUMMARY
          echo "- **Clean-up**: article-cli clean (from isolated venv)" >> $GITHUB_STEP_SUMMARY

      - name: Compile LaTeX document
        if: ${{{{ needs.workflow-setup.outputs.runner == 'self-texlive' }}}}
        run: |
          latexmk -shell-escape -pdf -file-line-error -interaction=nonstopmode  ${{{{ needs.workflow-setup.outputs.tex }}}}
          article-cli clean
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 🔨 LaTeX Compilation (Self-hosted)" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Engine**: latexmk with shell-escape" >> $GITHUB_STEP_SUMMARY
          echo "- **Runner**: self-texlive (self-hosted)" >> $GITHUB_STEP_SUMMARY
          echo "- **Source**: \`${{{{ needs.workflow-setup.outputs.tex }}}}\`" >> $GITHUB_STEP_SUMMARY
          echo "- **Clean-up**: article-cli clean (from isolated venv)" >> $GITHUB_STEP_SUMMARY

      - name: Rename PDF
        run: |
          mv {tex_base}.pdf ${{{{ needs.workflow-setup.outputs.pdf }}}}
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 📄 LaTeX Compilation Results" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          if [ -f "${{{{ needs.workflow-setup.outputs.pdf }}}}" ]; then
            file_size=$(du -h "${{{{ needs.workflow-setup.outputs.pdf }}}}" | cut -f1)
            echo "✅ **PDF Generated Successfully**" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
            echo "- **File**: \`${{{{ needs.workflow-setup.outputs.pdf }}}}\`" >> $GITHUB_STEP_SUMMARY
            echo "- **Size**: $file_size" >> $GITHUB_STEP_SUMMARY
            echo "- **Runner**: ${{{{ needs.workflow-setup.outputs.runner }}}}" >> $GITHUB_STEP_SUMMARY
            echo "- **Source**: \`${{{{ needs.workflow-setup.outputs.tex }}}}\`" >> $GITHUB_STEP_SUMMARY
          else
            echo "❌ **PDF Generation Failed**" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
            echo "Expected file: \`${{{{ needs.workflow-setup.outputs.pdf }}}}\`" >> $GITHUB_STEP_SUMMARY
          fi

      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{{{ needs.workflow-setup.outputs.pdf }}}}
          path: ${{{{ needs.workflow-setup.outputs.pdf }}}}
      - name: Upload Full Artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{{{ needs.workflow-setup.outputs.prefixwithref }}}}
          path: |
            ./*.tex
            ./*.bib
            ./*.sty
            ./*.cls
            ./*.gin
            ./*.bbl
            ./*.tikz
            ./${{{{ needs.workflow-setup.outputs.pdf }}}}
            ./README.md
            ./fig-*
            ./data/*
            !./.git*
            !./.github*
            !./.vscode*
            !./.idea*
            !./.DS_Store*
            !./.gitignore*

      - name: Generate build summary
        if: always()
        run: |
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 📦 Artifact Upload" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Artifact Name**: \`${{{{ needs.workflow-setup.outputs.prefixwithref }}}}\`" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Included Files:" >> $GITHUB_STEP_SUMMARY
          echo "- LaTeX source files (\*.tex, \*.sty, \*.cls)" >> $GITHUB_STEP_SUMMARY
          echo "- Bibliography files (\*.bib)" >> $GITHUB_STEP_SUMMARY
          echo "- Generated PDF: \`${{{{ needs.workflow-setup.outputs.pdf }}}}\`" >> $GITHUB_STEP_SUMMARY
          echo "- Git info files (\*.gin)" >> $GITHUB_STEP_SUMMARY
          echo "- Figures and data files" >> $GITHUB_STEP_SUMMARY

  check:
      needs: [build_latex,workflow-setup]
      runs-on: ${{{{ needs.workflow-setup.outputs.runner }}}}
      name: Check LaTeX Artifact
      steps:
      -
        name: Download Artifact
        uses: actions/download-artifact@v4
        with:
          name: ${{{{ needs.workflow-setup.outputs.prefixwithref }}}}
          path: ${{{{ github.workspace }}}}/artifact
      -
        name: Set up Python and uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
          enable-cache: false
      -
        name: Set up Python
        run: uv python install 3.11
      -
        name: Create virtual environment and install article-cli
        run: |
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## ⚡ Check Environment Setup" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY

          start_time=$(date +%s)
          uv venv .venv --python 3.11
          echo "VIRTUAL_ENV=${{PWD}}/.venv" >> $GITHUB_ENV
          echo "${{PWD}}/.venv/bin" >> $GITHUB_PATH
          uv pip install "article-cli>=1.1.0"
          end_time=$(date +%s)
          duration=$((end_time - start_time))

          echo "✅ **Check Environment Ready**" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Setup time**: ${{duration}}s (with uv cache)" >> $GITHUB_STEP_SUMMARY
          echo "- **Environment**: Isolated from build job" >> $GITHUB_STEP_SUMMARY
          echo "- **Purpose**: Artifact verification" >> $GITHUB_STEP_SUMMARY
      -
        name: List Artifact
        run: |
          ls -R ${{{{ github.workspace }}}}
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 🔍 Artifact Check" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Artifact**: \`${{{{ needs.workflow-setup.outputs.prefixwithref }}}}\`" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Artifact Contents:" >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
          ls -la ${{{{ github.workspace }}}}/artifact/ >> $GITHUB_STEP_SUMMARY
          echo "\`\`\`" >> $GITHUB_STEP_SUMMARY
      -
        name: Check compilation of LaTeX document from artifact
        if: ${{{{ needs.workflow-setup.outputs.runner == 'ubuntu-latest' }}}}
        uses: xu-cheng/latex-action@v3
        with:
          root_file: ${{{{ needs.workflow-setup.outputs.tex }}}}
          latexmk_shell_escape: true
          working_directory: ${{{{ github.workspace }}}}/artifact
      -
        name: Generate artifact verification summary (Ubuntu)
        if: ${{{{ needs.workflow-setup.outputs.runner == 'ubuntu-latest' }}}}
        run: |
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "✅ **Artifact Verification Completed (Ubuntu)**" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **LaTeX compilation from artifact**: Success" >> $GITHUB_STEP_SUMMARY
          echo "- **Runner**: ${{{{ needs.workflow-setup.outputs.runner }}}}" >> $GITHUB_STEP_SUMMARY
          echo "- **Clean-up**: Not needed (artifact already cleaned)" >> $GITHUB_STEP_SUMMARY
      -
        name: Check compilation of LaTeX document from artifact
        if: ${{{{ needs.workflow-setup.outputs.runner == 'self-texlive' }}}}
        run: |
          latexmk -shell-escape -pdf -file-line-error -interaction=nonstopmode  ${{{{ needs.workflow-setup.outputs.tex }}}}
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "✅ **Artifact Verification Completed**" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **LaTeX compilation from artifact**: Success" >> $GITHUB_STEP_SUMMARY
          echo "- **Runner**: ${{{{ needs.workflow-setup.outputs.runner }}}}" >> $GITHUB_STEP_SUMMARY
          echo "- **Clean-up**: Not needed (artifact already cleaned)" >> $GITHUB_STEP_SUMMARY
        working-directory: ${{{{ github.workspace }}}}/artifact

  release:
    needs: [workflow-setup,build_latex, check]
    runs-on: ${{{{ needs.workflow-setup.outputs.runner }}}}
    name: Create Release
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      - name: Download Artifact
        uses: actions/download-artifact@v4
        with:
          name: ${{{{ needs.workflow-setup.outputs.prefixwithref }}}}
          path: ${{{{ github.workspace }}}}/artifact

      - name: Archive Article
        run: |
          temp_dir=$(mktemp -d)
          tar -czvf "${{temp_dir}}/${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.tar.gz" -C artifact ./
          mv "${{temp_dir}}/${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.tar.gz" ./
          rm -rf "$temp_dir"

          # Generate release summary
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 🚀 Release Preparation" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Tag**: \`${{{{ github.ref_name }}}}\`" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### Release Assets:" >> $GITHUB_STEP_SUMMARY

          if [ -f "artifact/${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.pdf" ]; then
            pdf_size=$(du -h "artifact/${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.pdf" | cut -f1)
            echo "- 📄 **PDF**: \`${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.pdf\` ($pdf_size)" >> $GITHUB_STEP_SUMMARY
          fi

          if [ -f "${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.tar.gz" ]; then
            archive_size=$(du -h "${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.tar.gz" | cut -f1)
            echo "- 📦 **Archive**: \`${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.tar.gz\` ($archive_size)" >> $GITHUB_STEP_SUMMARY
          fi

      - name: Create Release
        id: create_release
        uses: softprops/action-gh-release@v2
        with:
          draft: false
          prerelease: ${{{{ contains(github.ref, 'alpha') || contains(github.ref, 'beta') || contains(github.ref, 'rc') || contains(github.ref, 'preview') }}}}
          name: Release ${{{{ github.ref_name }}}}
          generate_release_notes: true
          tag_name: ${{{{ github.ref }}}}
          token: ${{{{ secrets.GITHUB_TOKEN }}}}
          files: |
            artifact/${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.pdf
            ${{{{ needs.workflow-setup.outputs.prefixwithref }}}}.tar.gz

      - name: Generate release summary
        if: always()
        run: |
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## 🎉 Release Created" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          if [ "${{{{ steps.create_release.outcome }}}}" = "success" ]; then
            echo "✅ **Release Published Successfully**" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
            echo "- **Release**: [${{{{ github.ref_name }}}}](${{{{ steps.create_release.outputs.url }}}})" >> $GITHUB_STEP_SUMMARY
            echo "- **Type**: ${{{{ contains(github.ref, 'alpha') && 'Pre-release' || contains(github.ref, 'beta') && 'Pre-release' || contains(github.ref, 'rc') && 'Pre-release' || contains(github.ref, 'preview') && 'Pre-release' || 'Stable Release' }}}}" >> $GITHUB_STEP_SUMMARY
            echo "- **Assets**: PDF + Source Archive" >> $GITHUB_STEP_SUMMARY
            echo "- **Notes**: Auto-generated from commits" >> $GITHUB_STEP_SUMMARY
          else
            echo "❌ **Release Creation Failed**" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
            echo "Please check the workflow logs for details." >> $GITHUB_STEP_SUMMARY
          fi
'''

    def _create_pyproject(
        self,
        project_name: str,
        title: str,
        authors: List[str],
        group_id: str,
        force: bool,
    ) -> bool:
        """
        Create pyproject.toml file

        Args:
            project_name: Name of the project
            title: Article title
            authors: List of author names
            group_id: Zotero group ID
            force: Overwrite if exists

        Returns:
            True if successful
        """
        pyproject_path = self.repo_path / "pyproject.toml"

        if pyproject_path.exists() and not force:
            print_info(
                f"pyproject.toml already exists (use --force to overwrite)"
            )
            return True

        # Format authors for TOML
        authors_toml = ",\n    ".join([f'{{name = "{author}"}}' for author in authors])

        pyproject_content = f'''# Article Repository Dependency Management
# This file manages dependencies for the LaTeX article project

[project]
name = "{project_name}"
version = "0.1.0"
description = "{title}"
authors = [
    {authors_toml},
]
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "article-cli>=1.1.0",
    # Add other dependencies your article might need:
    # "matplotlib>=3.5.0",
    # "numpy>=1.20.0",
    # "pandas>=1.3.0",
]

# Configuration for article-cli (embedded in pyproject.toml)
[tool.article-cli.zotero]
group_id = "{group_id}"  # Zotero group ID for this project
# api_key = "your_api_key_here"  # Uncomment and add your API key or use ZOTERO_API_KEY env variable
output_file = "references.bib"

[tool.article-cli.git]
auto_push = false
default_branch = "main"

[tool.article-cli.latex]
clean_extensions = [
    ".aux", ".bbl", ".blg", ".log", ".out", ".pyg",
    ".fls", ".synctex.gz", ".toc", ".fdb_latexmk",
    ".idx", ".ilg", ".ind", ".lof", ".lot"
]
'''

        pyproject_path.write_text(pyproject_content)
        print_success(f"Created: {pyproject_path.relative_to(self.repo_path)}")
        return True

    def _create_readme(
        self,
        project_name: str,
        title: str,
        authors: List[str],
        tex_file: str,
        force: bool,
    ) -> bool:
        """
        Create README.md file

        Args:
            project_name: Name of the project
            title: Article title
            authors: List of author names
            tex_file: Main .tex filename
            force: Overwrite if exists

        Returns:
            True if successful
        """
        readme_path = self.repo_path / "README.md"

        if readme_path.exists() and not force:
            print_info(f"README.md already exists (use --force to overwrite)")
            return True

        authors_list = "\n".join([f"- {author}" for author in authors])

        readme_content = f'''# {title}

## Authors

{authors_list}

## Overview

This repository contains the LaTeX source for the article "{title}".

## Prerequisites

- Python 3.8+ (for bibliography management)
- LaTeX distribution (TeX Live recommended)
- Git with gitinfo2 package

## Setup

1. **Install article-cli**:
   ```bash
   pip install article-cli
   ```

2. **Setup git hooks**:
   ```bash
   article-cli setup
   ```

3. **Configure Zotero** (for bibliography management):
   
   Add your Zotero API key as a secret in GitHub:
   - Go to Repository Settings → Secrets → Actions
   - Add `ZOTERO_API_KEY` with your API key

   Or set it locally:
   ```bash
   export ZOTERO_API_KEY="your_api_key_here"
   ```

4. **Update bibliography**:
   ```bash
   article-cli update-bibtex
   ```

## Building the Document

### Local Build

```bash
latexmk -pdf {tex_file}
```

### Clean Build Files

```bash
article-cli clean
```

## CI/CD

This repository uses GitHub Actions for automated PDF compilation:

- **On push to main**: Compiles and uploads PDF artifact
- **On pull request**: Compiles and verifies the document
- **On tag push (v*)**: Creates a GitHub release with PDF

## Project Structure

```
.
├── {tex_file}              # Main LaTeX document
├── references.bib          # Bibliography (managed via Zotero)
├── pyproject.toml          # Project configuration
├── README.md               # This file
└── .github/
    └── workflows/
        └── latex.yml       # CI/CD pipeline
```

## article-cli Commands

```bash
# Setup repository
article-cli setup

# Update bibliography from Zotero
article-cli update-bibtex

# Clean LaTeX build files
article-cli clean

# Create a release
article-cli create v1.0.0

# List releases
article-cli list

# Show configuration
article-cli config show
```

## Development Workflow

1. Make changes to LaTeX source files
2. Update bibliography if needed: `article-cli update-bibtex`
3. Build locally: `latexmk -pdf {tex_file}`
4. Commit and push changes
5. Create a release tag for publication: `article-cli create v1.0.0 --push`

## License

[Specify your license here]

## Citation

```bibtex
@article{{{project_name},
  title = {{{title}}},
  author = {{{', '.join(authors)}}},
  year = {{2025}},
  url = {{https://github.com/feelpp/{project_name}}}
}}
```
'''

        readme_path.write_text(readme_content)
        print_success(f"Created: {readme_path.relative_to(self.repo_path)}")
        return True

    def _create_gitignore(self, force: bool) -> bool:
        """
        Create or update .gitignore file with LaTeX-specific entries

        Args:
            force: Overwrite if exists

        Returns:
            True if successful
        """
        gitignore_path = self.repo_path / ".gitignore"

        latex_ignores = """
# LaTeX build files
*.aux
*.bbl
*.blg
*.log
*.out
*.toc
*.fdb_latexmk
*.fls
*.synctex.gz
*.pdf
*.dvi
*.ps
*.idx
*.ilg
*.ind
*.lof
*.lot

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
.pytest_cache/
.mypy_cache/

# Editor
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# article-cli
.article-cli.toml.backup
references.bib.backup
"""

        if gitignore_path.exists() and not force:
            # Append if not already present
            existing = gitignore_path.read_text()
            if "LaTeX build files" not in existing:
                with open(gitignore_path, "a") as f:
                    f.write(latex_ignores)
                print_info("Updated .gitignore with LaTeX entries")
            else:
                print_info(".gitignore already contains LaTeX entries")
        else:
            gitignore_path.write_text(latex_ignores.lstrip())
            print_success(f"Created: {gitignore_path.relative_to(self.repo_path)}")

        return True

    def _create_vscode_settings(self, force: bool) -> bool:
        """
        Create VS Code settings for LaTeX Workshop

        Args:
            force: Overwrite if exists

        Returns:
            True if successful
        """
        vscode_settings_path = self.repo_path / ".vscode" / "settings.json"

        if vscode_settings_path.exists() and not force:
            print_info(".vscode/settings.json already exists (use --force to overwrite)")
            return True

        settings_content = '''{
    "latex-workshop.latex.recipes": [
        {
            "name": "latexmk-pdf",
            "tools": [
                "latexmk-shell-escape"
            ]
        },
        {
            "name": "pdflatex-shell-escape-recipe",
            "tools": [
                "pdflatex-shell-escape"
            ]
        }
    ],
    "latex-workshop.latex.tools": [
        {
            "name": "latexmk-shell-escape",
            "command": "latexmk",
            "args": [
                "--shell-escape",
                "-pdf",
                "-interaction=nonstopmode",
                "-synctex=1",
                "%DOC%"
            ],
            "env": {}
        },
        {
            "name": "pdflatex-shell-escape",
            "command": "pdflatex",
            "args": [
                "--shell-escape",
                "-synctex=1",
                "-interaction=nonstopmode",
                "-file-line-error",
                "%DOC%"
            ]
        }
    ],
    "latex-workshop.latex.autoBuild.run": "onSave",
    "latex-workshop.latex.autoBuild.enabled": true,
    "latex-workshop.latex.build.showOutput": "always",
    "latex-workshop.latex.outDir": "%DIR%",
    "latex-workshop.latex.clean.subfolder.enabled": true,
    "latex-workshop.message.badbox.show": "none",
    "workbench.editor.pinnedTabsOnSeparateRow": true,
    "ltex.latex.commands": {
        "\\\\author{}": "ignore",
        "\\\\IfFileExists{}{}": "ignore",
        "\\\\todo{}": "ignore",
        "\\\\todo[]{}": "ignore",
        "\\\\ts{}": "ignore",
        "\\\\cp{}": "ignore",
        "\\\\pgfmathprintnumber{}": "dummy",
        "\\\\feelpp{}": "dummy",
        "\\\\pgfplotstableread[]{}": "ignore",
        "\\\\xpatchcmd{}{}{}{}{}": "ignore"
    },
    "ltex.enabled": true,
    "ltex.language": "en-US"
}
'''

        vscode_settings_path.write_text(settings_content)
        print_success(f"Created: {vscode_settings_path.relative_to(self.repo_path)}")

        # Create ltex dictionary files
        self._create_ltex_files(force)

        return True

    def _create_ltex_files(self, force: bool) -> bool:
        """
        Create LTeX dictionary and false positives files

        Args:
            force: Overwrite if exists

        Returns:
            True if successful
        """
        # Dictionary file with common LaTeX/math terms
        dictionary_path = self.repo_path / ".vscode" / "ltex.dictionary.en-US.txt"
        if not dictionary_path.exists() or force:
            dictionary_content = """PDEs
PDE
Galerkin
Sobolev
coercivity
pointwise
functionals
parametrical
"""
            dictionary_path.write_text(dictionary_content)
            print_info(f"Created: {dictionary_path.relative_to(self.repo_path)}")

        # Hidden false positives file (empty initially)
        false_positives_path = self.repo_path / ".vscode" / "ltex.hiddenFalsePositives.en-US.txt"
        if not false_positives_path.exists() or force:
            false_positives_path.write_text("")
            print_info(f"Created: {false_positives_path.relative_to(self.repo_path)}")

        return True

    def _create_git_hooks(self, force: bool) -> bool:
        """
        Create git hooks directory with post-commit hook for gitinfo2

        Args:
            force: Overwrite if exists

        Returns:
            True if successful
        """
        post_commit_path = self.repo_path / "hooks" / "post-commit"

        if post_commit_path.exists() and not force:
            print_info("hooks/post-commit already exists (use --force to overwrite)")
            return True

        # gitinfo2 post-commit hook
        post_commit_content = '''#!/bin/sh
# Copyright 2015 Brent Longborough
# Part of gitinfo2 package Version 2
# Release 2.0.7 2015-11-22
# Please read gitinfo2.pdf for licencing and other details
# -----------------------------------------------------
# Post-{commit,checkout,merge} hook for the gitinfo2 package
#
# Get the first tag found in the history from the current HEAD
FIRSTTAG=$(git describe --tags --always --dirty='-*' 2>/dev/null)
# Get the first tag in history that looks like a Release
RELTAG=$(git describe --tags --long --always --dirty='-*' --match 'v[0-9]*\\.[0-9]*\\.[0-9]*' 2>/dev/null)
# Hoover up the metadata
git --no-pager log -1 --date=short --decorate=short \\
    --pretty=format:"\\usepackage[%
        shash={%h},
        lhash={%H},
        authname={%an},
        authemail={%ae},
        authsdate={%ad},
        authidate={%ai},
        authudate={%at},
        commname={%cn},
        commemail={%ce},
        commsdate={%cd},
        commidate={%ci},
        commudate={%ct},
        refnames={%d},
        firsttagdescribe={$FIRSTTAG},
        reltag={$RELTAG}
    ]{gitexinfo}" HEAD > .git/gitHeadInfo.gin
'''

        post_commit_path.write_text(post_commit_content)
        
        # Make the hook executable
        import stat
        post_commit_path.chmod(post_commit_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        print_success(f"Created: {post_commit_path.relative_to(self.repo_path)}")
        print_info("Made post-commit hook executable")
        
        return True
