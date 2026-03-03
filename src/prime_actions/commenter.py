from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prime_actions.github_api import create_pr_comment, create_review_comment

if TYPE_CHECKING:
    from prime_actions.models import PasswordFinding, PRContext

LOGGER = logging.getLogger(__name__)

REVIEW_COMMENT_BODY = "Remove it please \U0001f604"


def post_review_comments(
    context: PRContext,
    findings: list[PasswordFinding],
) -> int:
    posted = 0
    for finding in findings:
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
        "## PR Password Scanner Summary\n\n"
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
