from __future__ import annotations

import logging
from typing import Any

import requests

from prime_actions.models import PRContext, PRFile

LOGGER = logging.getLogger(__name__)

_API_BASE = "https://api.github.com"
_PER_PAGE = 100

_PERMISSIONS_ERROR_MSG = (
    "The provided GitHub token does not have 'pull-requests: write' permission. "
    "Please add the following to your workflow file:\n\n"
    "permissions:\n"
    "  pull-requests: write"
)


class InsufficientPermissionsError(Exception):
    pass


def verify_pr_write_permission(context: PRContext) -> None:
    url = f"{_API_BASE}/repos/{context.owner}/{context.repo}/pulls/{context.pr_number}/comments"
    response = requests.post(
        url,
        headers=_headers(context.token),
        json={},
        timeout=10,
    )
    if response.status_code == 403:
        raise InsufficientPermissionsError(_PERMISSIONS_ERROR_MSG)


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_pr_files(context: PRContext) -> list[PRFile]:
    url = f"{_API_BASE}/repos/{context.owner}/{context.repo}/pulls/{context.pr_number}/files"
    files: list[PRFile] = []
    page = 1

    while True:
        response = requests.get(
            url,
            headers=_headers(context.token),
            params={"per_page": _PER_PAGE, "page": page},
            timeout=10,
        )
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()
        if not data:
            break

        files.extend(
            PRFile(
                filename=item["filename"],
                patch=item.get("patch"),
                status=item["status"],
            )
            for item in data
        )

        if len(data) < _PER_PAGE:
            break
        page += 1

    LOGGER.info("Listed %d files from PR #%d", len(files), context.pr_number)
    return files


def list_review_comments(context: PRContext) -> list[dict[str, Any]]:
    url = f"{_API_BASE}/repos/{context.owner}/{context.repo}/pulls/{context.pr_number}/comments"
    comments: list[dict[str, Any]] = []
    page = 1

    while True:
        response = requests.get(
            url,
            headers=_headers(context.token),
            params={"per_page": _PER_PAGE, "page": page},
            timeout=10,
        )
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()
        if not data:
            break

        comments.extend(data)

        if len(data) < _PER_PAGE:
            break
        page += 1

    LOGGER.info("Listed %d review comments from PR #%d", len(comments), context.pr_number)
    return comments


def create_review_comment(
    context: PRContext,
    file_path: str,
    line: int,
    body: str,
) -> None:
    url = f"{_API_BASE}/repos/{context.owner}/{context.repo}/pulls/{context.pr_number}/comments"
    payload = {
        "body": body,
        "commit_id": context.head_sha,
        "path": file_path,
        "line": line,
        "side": "RIGHT",
    }
    response = requests.post(
        url,
        headers=_headers(context.token),
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    LOGGER.info("Posted review comment on %s:%d", file_path, line)


def create_pr_comment(context: PRContext, body: str) -> None:
    url = f"{_API_BASE}/repos/{context.owner}/{context.repo}/issues/{context.pr_number}/comments"
    response = requests.post(
        url,
        headers=_headers(context.token),
        json={"body": body},
        timeout=10,
    )
    response.raise_for_status()
    LOGGER.info("Posted summary comment on PR #%d", context.pr_number)
