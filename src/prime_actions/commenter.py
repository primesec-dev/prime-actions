from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prime_actions.github_api import (
    create_pr_comment,
    create_review_comment,
    list_review_comments,
)

if TYPE_CHECKING:
    from prime_actions.models import PasswordFinding, PRContext

LOGGER = logging.getLogger(__name__)

_LOGO_URL = (
    "https://raw.githubusercontent.com/primesec-dev/prime-actions/main/assets/prime-logo.png"
)
_BRAND = f'<img src="{_LOGO_URL}" width="16" height="16" align="absmiddle"> **Prime**'

REVIEW_COMMENT_BODY = f"{_BRAND} \u2014 Remove it please \U0001f604"


def _already_commented_locations(
    context: PRContext,
    body: str,
) -> set[tuple[str, int]]:
    comments = list_review_comments(context)
    return {
        (c["path"], c["line"])
        for c in comments
        if c.get("body") == body and c.get("path") and c.get("line") is not None
    }


def post_review_comments(
    context: PRContext,
    findings: list[PasswordFinding],
) -> int:
    already_commented = _already_commented_locations(context, REVIEW_COMMENT_BODY)

    posted = 0
    for finding in findings:
        if (finding.file_path, finding.line) in already_commented:
            LOGGER.info(
                "Skipping already commented %s:%d",
                finding.file_path,
                finding.line,
            )
            continue
        try:
            create_review_comment(
                context=context,
                file_path=finding.file_path,
                line=finding.line,
                body=REVIEW_COMMENT_BODY,
            )
            posted += 1
        except Exception:
            LOGGER.exception(
                "Failed to post review comment on %s:%d",
                finding.file_path,
                finding.line,
            )
    return posted


def build_summary(total_lines: int, findings_count: int) -> str:
    return (
        f"## {_BRAND} | Password Scanner Summary\n\n"
        "| Metric | Count |\n"
        "| --- | --- |\n"
        f"| Total added lines in PR | {total_lines} |\n"
        f"| Password occurrences found | {findings_count} |\n"
    )


def post_summary(
    context: PRContext,
    total_lines: int,
    findings_count: int,
) -> None:
    body = build_summary(total_lines, findings_count)
    try:
        create_pr_comment(context=context, body=body)
    except Exception:
        LOGGER.exception("Failed to post summary comment on PR #%d", context.pr_number)
