from __future__ import annotations

from prime_actions.models import PRFile
from prime_actions.scanner import count_added_lines, scan_file, scan_files


class TestScanFile:
    def test_single_password_found(self, pr_file_single_password: PRFile) -> None:
        findings = scan_file(pr_file_single_password)
        assert len(findings) == 1
        assert findings[0].file_path == "config.py"
        assert findings[0].line == 4
        assert "PASSWORD" in findings[0].content

    def test_multiple_passwords_found(self, pr_file_multiple_passwords: PRFile) -> None:
        findings = scan_file(pr_file_multiple_passwords)
        assert len(findings) == 3
        assert findings[0].line == 1
        assert findings[1].line == 3
        assert findings[2].line == 4

    def test_no_password_returns_empty(self, pr_file_no_password: PRFile) -> None:
        findings = scan_file(pr_file_no_password)
        assert findings == []

    def test_binary_file_returns_empty(self, pr_file_binary: PRFile) -> None:
        findings = scan_file(pr_file_binary)
        assert findings == []

    def test_password_in_context_not_flagged(
        self, pr_file_password_in_context_only: PRFile
    ) -> None:
        findings = scan_file(pr_file_password_in_context_only)
        assert findings == []

    def test_multiple_hunks(self, pr_file_multiple_hunks: PRFile) -> None:
        findings = scan_file(pr_file_multiple_hunks)
        assert len(findings) == 1
        assert findings[0].file_path == "app.py"
        assert findings[0].line == 14
        assert "password" in findings[0].content

    def test_case_insensitive_matching(self, pr_file_mixed_case: PRFile) -> None:
        findings = scan_file(pr_file_mixed_case)
        assert len(findings) == 2
        assert findings[0].content.strip() == 'Password = "mixed"'
        assert findings[1].content.strip() == 'pAsSwOrD = "weird"'

    def test_empty_patch_string(self) -> None:
        pr_file = PRFile(filename="empty.py", patch="", status="modified")
        findings = scan_file(pr_file)
        assert findings == []


class TestScanFiles:
    def test_aggregates_across_files(
        self, pr_file_single_password: PRFile, pr_file_multiple_passwords: PRFile
    ) -> None:
        findings = scan_files([pr_file_single_password, pr_file_multiple_passwords])
        assert len(findings) == 4

    def test_empty_file_list(self) -> None:
        findings = scan_files([])
        assert findings == []

    def test_skips_binary_files(
        self, pr_file_binary: PRFile, pr_file_single_password: PRFile
    ) -> None:
        findings = scan_files([pr_file_binary, pr_file_single_password])
        assert len(findings) == 1


class TestCountAddedLines:
    def test_counts_added_lines_only(
        self, pr_file_single_password: PRFile, pr_file_no_password: PRFile
    ) -> None:
        total = count_added_lines([pr_file_single_password, pr_file_no_password])
        assert total == 8

    def test_ignores_binary_files(self, pr_file_binary: PRFile) -> None:
        total = count_added_lines([pr_file_binary])
        assert total == 0

    def test_ignores_removed_and_context_lines(
        self, pr_file_password_in_context_only: PRFile
    ) -> None:
        total = count_added_lines([pr_file_password_in_context_only])
        assert total == 1

    def test_multiple_hunks(self, pr_file_multiple_hunks: PRFile) -> None:
        total = count_added_lines([pr_file_multiple_hunks])
        assert total == 2

    def test_empty_list(self) -> None:
        total = count_added_lines([])
        assert total == 0
