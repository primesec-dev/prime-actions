from __future__ import annotations

import logging
from typing import Any

import requests

from prime_actions.models import PRContext, PRFile

LOGGER = logging.getLogger(__name__)

_API_BASE = "https://api.github.com"
_PER_PAGE = 100


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

        for item in data:
            files.append(
                PRFile(
                    filename=item["filename"],
                    patch=item.get("patch"),
                    status=item["status"],
                )
            )

        if len(data) < _PER_PAGE:
            break
        page += 1

    LOGGER.info("Listed %d files from PR #%d", len(files), context.pr_number)
    return files


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
