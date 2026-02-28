"""Integration tests for threshold consistency within each skill.

This module verifies that threshold values mentioned in REQ-D01, REQ-D02, REQ-D03
appear consistently across SKILL.md, reference docs, and scripts within each skill.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"


class TestThresholdConsistency(unittest.TestCase):
    """Verify threshold values are consistent within each skill."""

    def _search_skill_files(self, skill_path, pattern, file_globs=None):
        """Search all files in a skill directory for a pattern.

        Args:
            skill_path: Path to skill directory
            pattern: Regex pattern to search for
            file_globs: List of file patterns to match (default: ["*.py", "*.md"])

        Returns:
            dict: Mapping from file path to list of (line_number, matched_text) tuples
        """
        if file_globs is None:
            file_globs = ["*.py", "*.md"]

        matches = {}
        for glob_pattern in file_globs:
            for file_path in skill_path.rglob(glob_pattern):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    file_matches = []
                    for line_num, line in enumerate(content.splitlines(), start=1):
                        match = re.search(pattern, line)
                        if match:
                            file_matches.append((line_num, line.strip()))
                    if file_matches:
                        matches[file_path] = file_matches
                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read
                    pass

        return matches

    def _extract_numeric_value(self, text, pattern):
        """Extract the first numeric value matching the pattern."""
        match = re.search(pattern, text)
        if match:
            # Try to extract a number from the matched text
            number_match = re.search(r'\d+\.?\d*', match.group(0))
            if number_match:
                return float(number_match.group(0))
        return None

    def test_pi_controller_k2_consistency(self):
        """REQ-D02: PI controller k2 coefficient must be consistent (0.4 per Soderlind 2003)."""
        skill_path = SKILLS_DIR / "core-numerical" / "numerical-integration"

        # Pattern to find k2 coefficient mentions
        pattern = r'k2\s*=\s*0\.[34]|k2.*0\.[34]|integral.*0\.[34]'

        matches = self._search_skill_files(skill_path, pattern)

        self.assertGreater(len(matches), 0,
                          "Should find at least one k2 coefficient reference")

        # Extract all k2 values found
        k2_values = []
        for file_path, file_matches in matches.items():
            for line_num, line in file_matches:
                # Look for k2 = 0.3 or k2 = 0.4
                if '0.3' in line:
                    k2_values.append((file_path, line_num, 0.3))
                elif '0.4' in line:
                    k2_values.append((file_path, line_num, 0.4))

        # Verify all values are 0.4 (the canonical value per Soderlind 2003)
        # Allow 0.3 only if it's mentioned as a historical note or correction
        wrong_values = []
        for file_path, line_num, value in k2_values:
            if value == 0.3:
                # Read the line context to check if it's a historical note
                content = file_path.read_text(encoding='utf-8')
                lines = content.splitlines()
                context = lines[line_num - 1] if line_num > 0 else ""

                # Allow if it mentions "updated from" or "was" or "previously"
                hist_words = ['updated', 'was', 'previously', 'old', 'prior']
                if not any(word in context.lower() for word in hist_words):
                    wrong_values.append((file_path, line_num, value, context))

        if wrong_values:
            msg = "Found incorrect k2 values (should be 0.4 per Soderlind 2003):\n"
            for file_path, line_num, value, context in wrong_values:
                msg += f"  {file_path.relative_to(REPO_ROOT)}:{line_num}: k2={value}\n"
                msg += f"    Context: {context[:80]}\n"
            self.fail(msg)

    def test_bo_dimension_threshold_consistency(self):
        """REQ-D03: BO dimension threshold must be consistent (10 per Frazier 2018)."""
        skill_path = SKILLS_DIR / "simulation-workflow" / "parameter-optimization"

        # Pattern to find BO dimension threshold mentions
        # Look for "5" or "10" in context of BO/Bayesian optimization and dimensions
        pattern = (
            r'(?:BO|Bayesian.*optimization).*(?:dimension|dim)'
            r'.*(?:threshold|limit|practical).*\d+'
            r'|dimension.*threshold.*\d+.*BO'
        )

        self._search_skill_files(skill_path, pattern)

        # Also search for numeric thresholds with BO context
        all_files = list(skill_path.rglob("*.py")) + list(skill_path.rglob("*.md"))
        threshold_values = []

        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                lines = content.splitlines()

                for line_num, line in enumerate(lines, start=1):
                    # Check for dimension threshold context
                    dim_match = any(
                        kw in line.lower() for kw in ['dimension', 'dim']
                    )
                    thresh_match = any(
                        kw in line.lower()
                        for kw in ['threshold', 'limit', 'practical']
                    )
                    if dim_match and thresh_match:
                        # Look for numbers 5 or 10 in this line or nearby lines
                        context_start = max(0, line_num - 2)
                        context_end = min(len(lines), line_num + 2)
                        context = '\n'.join(lines[context_start:context_end])

                        # Extract numeric values
                        for match in re.finditer(r'\b(5|10)\b', context):
                            value = int(match.group(1))
                            threshold_values.append((file_path, line_num, value, line))
            except (UnicodeDecodeError, PermissionError):
                pass

        # Check for the canonical value of 10
        if threshold_values:
            wrong_values = []
            for file_path, line_num, value, context in threshold_values:
                if value == 5:
                    # Check if it's a historical note or error
                    ctx_low = context.lower()
                    is_historical = (
                        'was' in ctx_low or 'previously' in ctx_low
                    )
                    if not is_historical and (
                        'threshold' in ctx_low or '=' in context
                    ):
                            wrong_values.append((file_path, line_num, value, context))

            if wrong_values:
                msg = (
                    "Found incorrect BO dimension threshold"
                    " values (should be 10 per Frazier 2018):\n"
                )
                for file_path, line_num, value, context in wrong_values:
                    rel = file_path.relative_to(REPO_ROOT)
                    msg += f"  {rel}:{line_num}: threshold={value}\n"
                    msg += f"    Context: {context[:80]}\n"
                self.fail(msg)

    def test_condition_number_threshold_consistency(self):
        """Condition number threshold for ill-conditioning should be consistent."""
        skill_path = SKILLS_DIR / "core-numerical" / "linear-solvers"

        # Pattern to find condition number thresholds (common values: 1e12, 1e14, 1e16)
        pattern = (
            r'condition.*(?:threshold|limit|warning).*1e\d+'
            r'|1e\d+.*condition.*(?:threshold|ill)'
        )

        self._search_skill_files(skill_path, pattern)

        # Extract all condition number thresholds
        cond_thresholds = []
        all_files = list(skill_path.rglob("*.py")) + list(skill_path.rglob("*.md"))

        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                for line_num, line in enumerate(content.splitlines(), start=1):
                    # Look for condition number thresholds
                    if 'condition' in line.lower() and ('1e' in line):
                        # Extract scientific notation numbers
                        for match in re.finditer(r'1e\d+', line):
                            value = match.group(0)
                            cond_thresholds.append((file_path, line_num, value, line))
            except (UnicodeDecodeError, PermissionError):
                pass

        # Verify thresholds are consistent across all files (when found)
        if len(cond_thresholds) > 1:
            unique_values = set(v for _, _, v, _ in cond_thresholds)
            if len(unique_values) > 1:
                msg = "Found inconsistent condition number thresholds in linear-solvers:\n"
                for value in sorted(unique_values):
                    occurrences = [(f, ln, ctx) for f, ln, v, ctx in cond_thresholds if v == value]
                    msg += f"  {value}: {len(occurrences)} occurrence(s)\n"
                    for f, ln, ctx in occurrences:
                        msg += f"    {f.relative_to(REPO_ROOT)}:{ln}: {ctx[:80]}\n"
                self.fail(msg)

    def test_cfl_limit_consistency_per_method(self):
        """CFL limits should be consistent for each time integration method."""
        skill_paths = [
            SKILLS_DIR / "core-numerical" / "numerical-stability",
            SKILLS_DIR / "core-numerical" / "time-stepping"
        ]

        # Common CFL limits to check: RK4 (~2.83), Forward Euler (1.0)
        cfl_values = {}

        for skill_path in skill_paths:
            all_files = list(skill_path.rglob("*.py")) + list(skill_path.rglob("*.md"))

            for file_path in all_files:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    for line_num, line in enumerate(content.splitlines(), start=1):
                        # Look for CFL mentions with RK4
                        if 'rk4' in line.lower() and 'cfl' in line.lower():
                            # Extract numeric values (common: 2.83, 2.8, 1.4)
                            for match in re.finditer(r'\d+\.\d+', line):
                                value = float(match.group(0))
                                if value > 1.0 and value < 5.0:  # Reasonable CFL range
                                    key = ('RK4', value)
                                    if key not in cfl_values:
                                        cfl_values[key] = []
                                    cfl_values[key].append((file_path, line_num, line))
                except (UnicodeDecodeError, PermissionError):
                    pass

        # Check for contradictory values for the same method
        rk4_values = [k[1] for k in cfl_values if k[0] == 'RK4']
        unique_rk4 = set(rk4_values)

        if len(unique_rk4) > 1:
            # Check if contradictory values exist (not just slight variations)
            values_list = sorted(unique_rk4)
            max_diff = max(values_list) - min(values_list)

            if max_diff > 0.5:  # Significant difference
                msg = f"Found contradictory RK4 CFL limits (REQ-A26): {values_list}\n"
                msg += "Expected consistent value (~2.83 per Gottlieb & Shu 1998)\n"
                for (method, value), occurrences in cfl_values.items():
                    if method == 'RK4':
                        msg += f"\n  CFL = {value}:\n"
                        for file_path, line_num, _line in occurrences[:3]:  # Show first 3
                            msg += f"    {file_path.relative_to(REPO_ROOT)}:{line_num}\n"
                self.fail(msg)

    def test_skewness_threshold_consistency(self):
        """Mesh skewness warning thresholds should be consistent."""
        skill_path = SKILLS_DIR / "core-numerical" / "mesh-generation"

        # Pattern for skewness thresholds (common: 0.9, 0.95)

        skewness_thresholds = []
        all_files = list(skill_path.rglob("*.py")) + list(skill_path.rglob("*.md"))

        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                for line_num, line in enumerate(content.splitlines(), start=1):
                    skew_words = ['threshold', 'warning', 'limit', 'max']
                    if 'skewness' in line.lower() and any(
                        w in line.lower() for w in skew_words
                    ):
                        # Extract decimal values between 0.5 and 1.0
                        for match in re.finditer(r'0\.\d+', line):
                            value = float(match.group(0))
                            if 0.5 <= value <= 1.0:
                                skewness_thresholds.append((file_path, line_num, value, line))
            except (UnicodeDecodeError, PermissionError):
                pass

        # Verify thresholds are consistent across all files
        if len(skewness_thresholds) > 1:
            unique_values = set(v for _, _, v, _ in skewness_thresholds)
            if len(unique_values) > 1:
                msg = (
                    "Found inconsistent skewness thresholds"
                    " in mesh-generation:\n"
                )
                for value in sorted(unique_values):
                    occurrences = [
                        (f, ln, ctx) for f, ln, v, ctx
                        in skewness_thresholds if v == value
                    ]
                    msg += f"  {value}: {len(occurrences)} occurrence(s)\n"
                    for f, ln, ctx in occurrences:
                        msg += f"    {f.relative_to(REPO_ROOT)}:{ln}: {ctx[:80]}\n"
                self.fail(msg)
        # If no thresholds found, the test is inconclusive (patterns may not match)

    def test_convergence_rate_classification_consistency(self):
        """Convergence rate classification thresholds should be consistent."""
        skill_path = SKILLS_DIR / "core-numerical" / "nonlinear-solvers"

        # Pattern for quadratic convergence detection (ratio ~ 2.0)
        convergence_patterns = []
        all_files = list(skill_path.rglob("*.py")) + list(skill_path.rglob("*.md"))

        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                for line_num, line in enumerate(content.splitlines(), start=1):
                    conv_kws = ['quadratic', 'superlinear', 'convergence rate']
                    if any(kw in line.lower() for kw in conv_kws):
                        # Look for threshold values near 2.0 (quadratic), 1.5 (superlinear)
                        for match in re.finditer(r'\b[12]\.\d+\b', line):
                            value = float(match.group(0))
                            if 1.2 <= value <= 2.5:
                                convergence_patterns.append((file_path, line_num, value, line))
            except (UnicodeDecodeError, PermissionError):
                pass

        # Only check consistency if patterns are found
        if not convergence_patterns:
            return

        quadratic = [(f, ln, v, ctx) for f, ln, v, ctx in convergence_patterns if v >= 1.8]
        superlinear = [(f, ln, v, ctx) for f, ln, v, ctx in convergence_patterns if v < 1.8]

        if len(quadratic) > 1:
            quad_values = set(v for _, _, v, _ in quadratic)
            if len(quad_values) > 1:
                msg = "Found inconsistent quadratic convergence thresholds in nonlinear-solvers:\n"
                for value in sorted(quad_values):
                    occurrences = [(f, ln, ctx) for f, ln, v, ctx in quadratic if v == value]
                    msg += f"  {value}: {len(occurrences)} occurrence(s)\n"
                    for f, ln, ctx in occurrences:
                        msg += f"    {f.relative_to(REPO_ROOT)}:{ln}: {ctx[:80]}\n"
                self.fail(msg)

        if len(superlinear) > 1:
            super_values = set(v for _, _, v, _ in superlinear)
            if len(super_values) > 1:
                msg = (
                    "Found inconsistent superlinear convergence"
                    " thresholds in nonlinear-solvers:\n"
                )
                for value in sorted(super_values):
                    occurrences = [(f, ln, ctx) for f, ln, v, ctx in superlinear if v == value]
                    msg += f"  {value}: {len(occurrences)} occurrence(s)\n"
                    for f, ln, ctx in occurrences:
                        msg += f"    {f.relative_to(REPO_ROOT)}:{ln}: {ctx[:80]}\n"
                self.fail(msg)


if __name__ == "__main__":
    unittest.main()
