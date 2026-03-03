from __future__ import annotations

import re

from prime_actions.models import PasswordFinding, PRFile

_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_PASSWORD_RE = re.compile(r"password", re.IGNORECASE)


def scan_file(pr_file: PRFile) -> list[PasswordFinding]:
    if pr_file.patch is None:
        return []
    return _scan_patch(pr_file.filename, pr_file.patch)


def scan_files(pr_files: list[PRFile]) -> list[PasswordFinding]:
    findings: list[PasswordFinding] = []
    for pr_file in pr_files:
        findings.extend(scan_file(pr_file))
    return findings


def count_added_lines(pr_files: list[PRFile]) -> int:
    total = 0
    for pr_file in pr_files:
        if pr_file.patch is None:
            continue
        for line in pr_file.patch.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                total += 1
    return total


def _scan_patch(file_path: str, patch: str) -> list[PasswordFinding]:
    findings: list[PasswordFinding] = []
    current_line = 0

    for raw_line in patch.splitlines():
        hunk_match = _HUNK_HEADER_RE.match(raw_line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            continue

        if raw_line.startswith("+++") or raw_line.startswith("---"):
            continue

        if raw_line.startswith("+"):
            content = raw_line[1:]
            if _PASSWORD_RE.search(content):
                findings.append(
                    PasswordFinding(
                        file_path=file_path,
                        line=current_line,
                        content=content,
                    )
                )
            current_line += 1
        elif raw_line.startswith("-"):
            pass
        else:
            current_line += 1

    return findings
