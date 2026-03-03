from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordFinding:
    file_path: str
    line: int
    content: str


@dataclass(frozen=True)
class PRContext:
    owner: str
    repo: str
    pr_number: int
    head_sha: str
    token: str


@dataclass(frozen=True)
class PRFile:
    filename: str
    patch: str | None
    status: str
