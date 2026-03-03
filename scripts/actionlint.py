"""Lint GitHub Actions workflow files for common misconfigurations."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

VALID_EVENTS = {
    "branch_protection_rule",
    "check_run",
    "check_suite",
    "create",
    "delete",
    "deployment",
    "deployment_status",
    "discussion",
    "discussion_comment",
    "fork",
    "gollum",
    "issue_comment",
    "issues",
    "label",
    "merge_group",
    "milestone",
    "page_build",
    "project",
    "project_card",
    "project_column",
    "public",
    "pull_request",
    "pull_request_review",
    "pull_request_review_comment",
    "pull_request_target",
    "push",
    "registry_package",
    "release",
    "repository_dispatch",
    "schedule",
    "status",
    "watch",
    "workflow_call",
    "workflow_dispatch",
    "workflow_run",
}

VALID_PERMISSIONS = {
    "actions",
    "attestations",
    "checks",
    "contents",
    "deployments",
    "discussions",
    "id-token",
    "issues",
    "packages",
    "pages",
    "pull-requests",
    "repository-projects",
    "security-events",
    "statuses",
}

VALID_PERMISSION_VALUES = {"read", "write", "none"}

STEP_ID_RE = re.compile(r"steps\.([a-zA-Z_][a-zA-Z0-9_-]*)\.outputs\.")
NEEDS_OUTPUT_RE = re.compile(r"needs\.([a-zA-Z_][a-zA-Z0-9_-]*)\.outputs\.")


class LintError:
    def __init__(self, file: str, message: str, location: str = "") -> None:
        self.file = file
        self.message = message
        self.location = location

    def __str__(self) -> str:
        loc = f" ({self.location})" if self.location else ""
        return f"{self.file}{loc}: {self.message}"


def lint_triggers(workflow: dict[str, object], file: str) -> list[LintError]:
    errors: list[LintError] = []
    on: object = workflow.get("on")
    if on is None:
        raw: dict[object, object] = workflow  # type: ignore[assignment]
        on = raw.get(True)
    if on is None:
        errors.append(LintError(file, "missing required key 'on'"))
        return errors

    if isinstance(on, str):
        events = [on]
    elif isinstance(on, list):
        events = on
    elif isinstance(on, dict):
        events = list(on.keys())
    else:
        errors.append(LintError(file, f"'on' has unexpected type: {type(on).__name__}"))
        return errors

    for event in events:
        if str(event) not in VALID_EVENTS:
            errors.append(LintError(file, f"unknown trigger event '{event}'"))

    return errors


def lint_permissions(perms: object, file: str, location: str) -> list[LintError]:
    errors: list[LintError] = []
    if isinstance(perms, dict):
        for key, value in perms.items():
            if key not in VALID_PERMISSIONS:
                errors.append(LintError(file, f"unknown permission '{key}'", location))
            if value not in VALID_PERMISSION_VALUES:
                errors.append(
                    LintError(file, f"invalid permission value '{value}' for '{key}'", location)
                )
    return errors


def lint_jobs(workflow: dict[str, object], file: str) -> list[LintError]:
    errors: list[LintError] = []
    jobs = workflow.get("jobs")
    if jobs is None:
        errors.append(LintError(file, "missing required key 'jobs'"))
        return errors
    if not isinstance(jobs, dict):
        errors.append(LintError(file, "'jobs' must be a mapping"))
        return errors

    job_ids = set(jobs.keys())

    for job_id, job_def in jobs.items():
        loc = f"job '{job_id}'"
        if not isinstance(job_def, dict):
            errors.append(LintError(file, "job definition must be a mapping", loc))
            continue

        has_runs_on = "runs-on" in job_def
        has_uses = "uses" in job_def
        if not has_runs_on and not has_uses:
            errors.append(LintError(file, "job must have 'runs-on' or 'uses'", loc))
        if has_runs_on and has_uses:
            errors.append(LintError(file, "job cannot have both 'runs-on' and 'uses'", loc))

        if "permissions" in job_def:
            errors.extend(lint_permissions(job_def["permissions"], file, loc))

        needs = job_def.get("needs")
        if needs is not None:
            needs_list = [needs] if isinstance(needs, str) else needs
            if isinstance(needs_list, list):
                for dep in needs_list:
                    if dep not in job_ids:
                        errors.append(
                            LintError(file, f"'needs' references unknown job '{dep}'", loc)
                        )

        errors.extend(_lint_job_needs_outputs(job_def, job_ids, file, loc))

        if has_runs_on:
            errors.extend(_lint_steps(job_def, file, loc))

    return errors


def _lint_job_needs_outputs(
    job_def: dict[str, object], job_ids: set[str], file: str, loc: str
) -> list[LintError]:
    errors: list[LintError] = []
    job_str = str(job_def)
    for match in NEEDS_OUTPUT_RE.finditer(job_str):
        ref_job = match.group(1)
        if ref_job not in job_ids:
            errors.append(LintError(file, f"references outputs from unknown job '{ref_job}'", loc))
    return errors


def _lint_steps(job_def: dict[str, object], file: str, job_loc: str) -> list[LintError]:
    errors: list[LintError] = []
    steps = job_def.get("steps")
    if steps is None:
        errors.append(LintError(file, "job with 'runs-on' must have 'steps'", job_loc))
        return errors
    if not isinstance(steps, list):
        errors.append(LintError(file, "'steps' must be a list", job_loc))
        return errors

    step_ids: set[str] = set()
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step_loc = f"{job_loc}, step {i}"
        if step_name := step.get("name"):
            step_loc = f"{job_loc}, step '{step_name}'"

        has_run = "run" in step
        has_uses = "uses" in step
        if not has_run and not has_uses:
            errors.append(LintError(file, "step must have 'run' or 'uses'", step_loc))
        if has_run and has_uses:
            errors.append(LintError(file, "step cannot have both 'run' and 'uses'", step_loc))

        step_id = step.get("id")
        if step_id is not None:
            if step_id in step_ids:
                errors.append(LintError(file, f"duplicate step id '{step_id}'", step_loc))
            step_ids.add(step_id)

    job_str = str(steps)
    for match in STEP_ID_RE.finditer(job_str):
        ref_id = match.group(1)
        if ref_id not in step_ids:
            errors.append(
                LintError(
                    file,
                    f"references outputs from unknown step id '{ref_id}'",
                    job_loc,
                )
            )

    return errors


def lint_file(path: Path) -> list[LintError]:
    file = str(path)
    try:
        content = path.read_text()
    except OSError as e:
        return [LintError(file, f"cannot read file: {e}")]

    try:
        workflow = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return [LintError(file, f"invalid YAML: {e}")]

    if not isinstance(workflow, dict):
        return [LintError(file, "workflow must be a YAML mapping")]

    errors: list[LintError] = []
    errors.extend(lint_triggers(workflow, file))

    if "permissions" in workflow:
        errors.extend(lint_permissions(workflow["permissions"], file, "top-level"))

    errors.extend(lint_jobs(workflow, file))
    return errors


def main() -> int:
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.is_dir():
        print(f"Error: {workflows_dir} directory not found", file=sys.stderr)
        return 1

    files = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    if not files:
        print(f"No workflow files found in {workflows_dir}", file=sys.stderr)
        return 1

    all_errors: list[LintError] = []
    for path in files:
        all_errors.extend(lint_file(path))

    if all_errors:
        for error in all_errors:
            print(f"::error::{error}")
        print(f"\n{len(all_errors)} error(s) found in {len(files)} workflow file(s)")
        return 1

    print(f"All {len(files)} workflow file(s) passed actionlint checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
