from __future__ import annotations

import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

from prime_actions.commenter import post_review_comments, post_summary
from prime_actions.github_api import list_pr_files
from prime_actions.models import PRContext
from prime_actions.scanner import count_added_lines, scan_files

LOGGER = logging.getLogger(__name__)


class TimeoutError(Exception):  # noqa: A001
    pass


def _on_timeout(signum: int, frame: Any) -> None:
    raise TimeoutError("Action timed out")


def _get_input(name: str, default: str = "") -> str:
    return os.environ.get(f"INPUT_{name.upper()}", default)


def _write_output(name: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with Path(output_file).open("a") as f:
            f.write(f"{name}={value}\n")


def _build_context() -> PRContext:
    token = _get_input("token")
    if not token:
        LOGGER.error("No GitHub token provided")
        sys.exit(1)

    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repository:
        LOGGER.error("Invalid GITHUB_REPOSITORY: %s", repository)
        sys.exit(1)
    owner, repo = repository.split("/", 1)

    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not Path(event_path).exists():
        LOGGER.error("GITHUB_EVENT_PATH not found: %s", event_path)
        sys.exit(1)

    with Path(event_path).open() as f:
        event: dict[str, Any] = json.load(f)

    pull_request = event.get("pull_request")
    if not pull_request:
        LOGGER.error("This action only runs on pull_request events")
        sys.exit(1)

    pr_number: int = pull_request["number"]
    head_sha: str = pull_request["head"]["sha"]

    return PRContext(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha,
        token=token,
    )


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    timeout_str = _get_input("timeout", "30")
    try:
        timeout = int(timeout_str)
    except ValueError:
        LOGGER.error("Invalid timeout value: %s", timeout_str)
        sys.exit(1)

    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _on_timeout)
        signal.alarm(timeout)

    try:
        context = _build_context()

        LOGGER.info(
            "Scanning PR #%d in %s/%s", context.pr_number, context.owner, context.repo
        )

        pr_files = list_pr_files(context)
        LOGGER.info("Found %d files in PR", len(pr_files))

        findings = scan_files(pr_files)
        total_lines = count_added_lines(pr_files)

        LOGGER.info(
            "Scan complete: %d added lines, %d password findings",
            total_lines,
            len(findings),
        )

        if findings:
            posted = post_review_comments(context, findings)
            LOGGER.info("Posted %d review comments", posted)

        post_summary(context, total_lines, len(findings))

        _write_output("total-lines", str(total_lines))
        _write_output("password-findings", str(len(findings)))

    except TimeoutError:
        LOGGER.exception("Action timed out after %d seconds", timeout)
        sys.exit(1)
    except Exception:
        LOGGER.exception("Action failed")
        sys.exit(1)
    finally:
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)
