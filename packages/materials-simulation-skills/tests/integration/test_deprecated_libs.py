"""Integration tests for absence of deprecated library names.

This module verifies REQ-E01 and REQ-E02: all references to deprecated libraries
(scikit-optimize, GPyOpt, skopt) have been replaced with maintained alternatives.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

# Deprecated libraries that should not appear in documentation
DEPRECATED_LIBRARIES = [
    "scikit-optimize",
    "skopt",
    "GPyOpt",
]

# Recommended replacement libraries (for informational purposes)
RECOMMENDED_REPLACEMENTS = [
    "BoTorch",
    "Optuna",
    "Ax",
]


class TestDeprecatedLibraries(unittest.TestCase):
    """Verify that deprecated library names do not appear in documentation."""

    def _search_files(self, pattern, file_globs=None, search_path=None):
        """Search files for a pattern.

        Args:
            pattern: Regex pattern to search for
            file_globs: List of file patterns to match (default: ["*.md"])
            search_path: Path to search in (default: SKILLS_DIR)

        Returns:
            dict: Mapping from file path to list of (line_number, matched_text) tuples
        """
        if file_globs is None:
            file_globs = ["*.md"]
        if search_path is None:
            search_path = SKILLS_DIR

        matches = {}
        for glob_pattern in file_globs:
            for file_path in search_path.rglob(glob_pattern):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    file_matches = []
                    for line_num, line in enumerate(content.splitlines(), start=1):
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            file_matches.append((line_num, line.strip()))
                    if file_matches:
                        matches[file_path] = file_matches
                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read
                    pass

        return matches

    def test_no_scikit_optimize_references(self):
        """REQ-E01: Verify scikit-optimize has been replaced with maintained alternatives."""
        # Search for various forms of the deprecated library name
        patterns = [
            r'\bscikit-optimize\b',
            r'\bskopt\b',
            r'sklearn\.optimize',  # Sometimes confused with scikit-optimize
        ]

        all_matches = {}
        for pattern in patterns:
            matches = self._search_files(pattern)
            all_matches.update(matches)

        if all_matches:
            msg = "Found references to deprecated scikit-optimize library (REQ-E01):\n"
            msg += "This library was archived in February 2024.\n"
            msg += "Replace with: BoTorch, Optuna, or Ax\n\n"
            for file_path, file_matches in sorted(all_matches.items()):
                msg += f"\n{file_path.relative_to(REPO_ROOT)}:\n"
                for line_num, line in file_matches:
                    msg += f"  Line {line_num}: {line[:100]}\n"
            self.fail(msg)

    def test_no_gpyopt_references(self):
        """REQ-E02: Verify GPyOpt has been replaced with maintained alternatives."""
        # Search for GPyOpt references
        patterns = [
            r'\bGPyOpt\b',
            r'\bgpyopt\b',
        ]

        all_matches = {}
        for pattern in patterns:
            matches = self._search_files(pattern)
            all_matches.update(matches)

        if all_matches:
            msg = "Found references to deprecated GPyOpt library (REQ-E02):\n"
            msg += "This library has been archived.\n"
            msg += "Replace with: BoTorch, Optuna, or Ax\n\n"
            for file_path, file_matches in sorted(all_matches.items()):
                msg += f"\n{file_path.relative_to(REPO_ROOT)}:\n"
                for line_num, line in file_matches:
                    msg += f"  Line {line_num}: {line[:100]}\n"
            self.fail(msg)

    def test_replacement_libraries_mentioned(self):
        """Verify that recommended replacement libraries are mentioned."""
        # Search for mentions of recommended replacements
        replacement_mentions = {}

        for library in RECOMMENDED_REPLACEMENTS:
            pattern = rf'\b{library}\b'
            matches = self._search_files(pattern)
            if matches:
                replacement_mentions[library] = len(matches)

        # We should find at least one recommended replacement
        self.assertGreater(
            len(replacement_mentions),
            0,
            "Expected to find at least one recommended replacement library "
            "(BoTorch, Optuna, or Ax) in the documentation"
        )

        # Print summary of replacement library mentions
        print("\nReplacement libraries found:")
        for library, count in sorted(replacement_mentions.items()):
            print(f"  {library}: {count} file(s)")

    def test_no_other_deprecated_optimization_libraries(self):
        """Check for other known deprecated or unmaintained optimization libraries."""
        # Additional libraries to check (less strict - just warn if found)
        additional_checks = {
            "hyperopt": "Consider Optuna as a maintained alternative",
            "spearmint": "Unmaintained since 2016, consider BoTorch or Optuna",
        }

        found_deprecated = []
        for library, recommendation in additional_checks.items():
            pattern = rf'\b{library}\b'
            matches = self._search_files(pattern)
            if matches:
                for file_path, file_matches in matches.items():
                    for line_num, _line in file_matches:
                        found_deprecated.append(
                            f"{file_path.relative_to(REPO_ROOT)}:{line_num}: "
                            f"Found '{library}' - {recommendation}"
                        )

        if found_deprecated:
            msg = "Found references to deprecated/unmaintained optimization libraries:\n"
            for entry in found_deprecated:
                msg += f"  {entry}\n"
            self.fail(msg)

    def test_installation_commands_valid(self):
        """Verify that library installation commands in docs reference maintained packages."""
        # Search for pip install commands
        pattern = r'pip\s+install\s+[\w\-\[\]]+'

        matches = self._search_files(pattern)

        deprecated_in_install = []
        for file_path, file_matches in matches.items():
            for line_num, line in file_matches:
                # Check if any deprecated library appears in install command
                for deprecated in DEPRECATED_LIBRARIES:
                    if deprecated.lower() in line.lower():
                        deprecated_in_install.append((file_path, line_num, line))

        if deprecated_in_install:
            msg = "Found deprecated libraries in installation commands:\n"
            for file_path, line_num, line in deprecated_in_install:
                msg += f"  {file_path.relative_to(REPO_ROOT)}:{line_num}\n"
                msg += f"    {line[:100]}\n"
            self.fail(msg)

    def test_import_statements_no_deprecated_libs(self):
        """Verify Python code examples don't import deprecated libraries."""
        # Search Python code files and markdown code blocks
        deprecated_imports = []

        # Check .py files
        for py_file in SKILLS_DIR.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                for line_num, line in enumerate(content.splitlines(), start=1):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        for deprecated in DEPRECATED_LIBRARIES:
                            # Check for "import skopt" or "from skopt import"
                            dep_pat = rf'\b{deprecated.replace("-", "[_-]")}\b'
                            if re.search(dep_pat, line, re.IGNORECASE):
                                deprecated_imports.append(
                                    (py_file, line_num, line.strip())
                                )
            except (UnicodeDecodeError, PermissionError):
                pass

        # Check markdown files for Python code blocks
        for md_file in SKILLS_DIR.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                in_python_block = False
                lines = content.splitlines()

                for line_num, line in enumerate(lines, start=1):
                    # Detect Python code block start
                    if re.match(r'```python', line, re.IGNORECASE):
                        in_python_block = True
                        continue
                    # Detect code block end
                    elif line.strip() == '```':
                        in_python_block = False
                        continue

                    # Check imports in Python blocks
                    if in_python_block and 'import ' in line:
                        for deprecated in DEPRECATED_LIBRARIES:
                            dep_pat = rf'\b{deprecated.replace("-", "[_-]")}\b'
                            if re.search(dep_pat, line, re.IGNORECASE):
                                deprecated_imports.append(
                                    (md_file, line_num, line.strip())
                                )
            except (UnicodeDecodeError, PermissionError):
                pass

        if deprecated_imports:
            msg = "Found imports of deprecated libraries in code:\n"
            for file_path, line_num, line in deprecated_imports:
                msg += f"  {file_path.relative_to(REPO_ROOT)}:{line_num}\n"
                msg += f"    {line[:100]}\n"
            self.fail(msg)

    def test_documentation_links_to_active_projects(self):
        """Verify documentation links point to active projects, not archived ones."""
        # Search for GitHub links that might point to archived repositories
        github_pattern = r'github\.com/[\w\-]+/[\w\-]+'

        matches = self._search_files(github_pattern)

        # Known archived repos to check for
        archived_repos = [
            "scikit-optimize/scikit-optimize",
            "SheffieldML/GPyOpt",
        ]

        archived_links = []
        for file_path, file_matches in matches.items():
            for line_num, line in file_matches:
                for archived in archived_repos:
                    if archived in line:
                        archived_links.append((file_path, line_num, line))

        if archived_links:
            msg = "Found links to archived GitHub repositories:\n"
            for file_path, line_num, line in archived_links:
                msg += f"  {file_path.relative_to(REPO_ROOT)}:{line_num}\n"
                msg += f"    {line[:100]}\n"
            self.fail(msg)


class TestOptionalDependencyLabeling(unittest.TestCase):
    """Verify that optional dependencies are properly labeled (REQ-E03)."""

    def test_sklearn_examples_are_labeled(self):
        """Code examples using sklearn should be labeled as optional."""
        sklearn_examples = []

        # Search markdown files for sklearn usage
        for md_file in SKILLS_DIR.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                lines = content.splitlines()
                in_code_block = False
                block_start = 0
                block_lines = []

                for line_num, line in enumerate(lines, start=1):
                    if re.match(r'```\w*', line):
                        if not in_code_block:
                            in_code_block = True
                            block_start = line_num
                            block_lines = []
                        else:
                            in_code_block = False
                            # Check if this block imports sklearn
                            block_text = '\n'.join(block_lines)
                            if 'sklearn' in block_text or 'scikit-learn' in block_text.lower():
                                # Check if the block or preceding lines have a label
                                context_start = max(0, block_start - 5)
                                context = '\n'.join(lines[context_start:block_start])

                                ctx_kws = [
                                    'optional', 'requires',
                                    'scikit-learn', 'sklearn',
                                ]
                                blk_kws = ['# requires', '# optional']
                                has_label = any(
                                    kw in context.lower() for kw in ctx_kws
                                ) or any(
                                    kw in block_text.lower() for kw in blk_kws
                                )

                                if not has_label:
                                    sklearn_examples.append(
                                        (md_file, block_start, block_text[:200])
                                    )
                    elif in_code_block:
                        block_lines.append(line)
            except (UnicodeDecodeError, PermissionError):
                pass

        if sklearn_examples:
            msg = (
                "Found sklearn code examples without optional dependency labels (REQ-E03).\n"
                "Add '# Requires: scikit-learn (optional)' or similar label before each block:\n"
            )
            for file_path, line_num, snippet in sklearn_examples[:5]:
                msg += f"  {file_path.relative_to(REPO_ROOT)}:{line_num}\n"
                msg += f"    {snippet[:80]}...\n"
            if len(sklearn_examples) > 5:
                msg += f"  ... and {len(sklearn_examples) - 5} more\n"
            self.fail(msg)


if __name__ == "__main__":
    unittest.main()
