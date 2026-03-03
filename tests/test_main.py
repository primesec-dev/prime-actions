from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from prime_actions.main import _build_context, _get_input, _write_output, run
from prime_actions.models import PRFile


@pytest.fixture()
def event_file(tmp_path: Path) -> Path:
    event = {
        "pull_request": {
            "number": 42,
            "head": {"sha": "abc123def456"},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event))
    return event_path


@pytest.fixture()
def github_env(event_file: Path, tmp_path: Path) -> dict[str, str]:
    output_file = tmp_path / "github_output.txt"
    output_file.touch()
    return {
        "INPUT_TOKEN": "ghp_test_token",
        "INPUT_TIMEOUT": "30",
        "GITHUB_REPOSITORY": "test-owner/test-repo",
        "GITHUB_EVENT_PATH": str(event_file),
        "GITHUB_OUTPUT": str(output_file),
    }


class TestGetInput:
    def test_reads_from_env(self) -> None:
        with patch.dict(os.environ, {"INPUT_TIMEOUT": "60"}):
            assert _get_input("timeout") == "60"

    def test_returns_default_when_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert _get_input("timeout", "30") == "30"

    def test_uppercases_name(self) -> None:
        with patch.dict(os.environ, {"INPUT_MY_INPUT": "value"}):
            assert _get_input("my_input") == "value"


class TestWriteOutput:
    def test_writes_to_github_output(self, tmp_path: Path) -> None:
        output_file = tmp_path / "output.txt"
        output_file.touch()
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            _write_output("total-lines", "42")
        assert "total-lines=42\n" in output_file.read_text()

    def test_appends_multiple_outputs(self, tmp_path: Path) -> None:
        output_file = tmp_path / "output.txt"
        output_file.touch()
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}):
            _write_output("total-lines", "42")
            _write_output("password-findings", "3")
        content = output_file.read_text()
        assert "total-lines=42\n" in content
        assert "password-findings=3\n" in content

    def test_noop_when_no_output_file(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            _write_output("key", "value")


class TestBuildContext:
    def test_builds_context_from_env(self, github_env: dict[str, str]) -> None:
        with patch.dict(os.environ, github_env, clear=True):
            ctx = _build_context()
        assert ctx.owner == "test-owner"
        assert ctx.repo == "test-repo"
        assert ctx.pr_number == 42
        assert ctx.head_sha == "abc123def456"
        assert ctx.token == "ghp_test_token"

    def test_exits_without_token(self, github_env: dict[str, str]) -> None:
        github_env.pop("INPUT_TOKEN")
        with patch.dict(os.environ, github_env, clear=True), pytest.raises(SystemExit):
            _build_context()

    def test_exits_with_invalid_repository(self, github_env: dict[str, str]) -> None:
        github_env["GITHUB_REPOSITORY"] = "invalid"
        with patch.dict(os.environ, github_env, clear=True), pytest.raises(SystemExit):
            _build_context()

    def test_exits_without_event_file(self, github_env: dict[str, str]) -> None:
        github_env["GITHUB_EVENT_PATH"] = "/nonexistent/event.json"
        with patch.dict(os.environ, github_env, clear=True), pytest.raises(SystemExit):
            _build_context()

    def test_exits_on_non_pr_event(self, github_env: dict[str, str], tmp_path: Path) -> None:
        non_pr_event = tmp_path / "push_event.json"
        non_pr_event.write_text(json.dumps({"ref": "refs/heads/main"}))
        github_env["GITHUB_EVENT_PATH"] = str(non_pr_event)
        with patch.dict(os.environ, github_env, clear=True), pytest.raises(SystemExit):
            _build_context()


def _make_mock_pr_files() -> list[Any]:
    return [
        PRFile(
            filename="config.py",
            patch='@@ -0,0 +1,3 @@\n+import os\n+DB_PASSWORD = "secret"\n+PORT = 5432',
            status="added",
        ),
        PRFile(
            filename="readme.md",
            patch="@@ -0,0 +1,1 @@\n+# Hello",
            status="added",
        ),
    ]


class TestRun:
    @patch("prime_actions.main.post_summary")
    @patch("prime_actions.main.post_review_comments")
    @patch("prime_actions.main.list_pr_files")
    def test_full_run_with_findings(
        self,
        mock_list_files: MagicMock,
        mock_post_comments: MagicMock,
        mock_post_summary: MagicMock,
        github_env: dict[str, str],
    ) -> None:
        mock_list_files.return_value = _make_mock_pr_files()
        mock_post_comments.return_value = 1

        with patch.dict(os.environ, github_env, clear=True):
            run()

        mock_list_files.assert_called_once()
        mock_post_comments.assert_called_once()
        mock_post_summary.assert_called_once()

        summary_args = mock_post_summary.call_args
        assert summary_args.args[1] == 4
        assert summary_args.args[2] == 1

        output_content = Path(github_env["GITHUB_OUTPUT"]).read_text()
        assert "total-lines=4" in output_content
        assert "password-findings=1" in output_content

    @patch("prime_actions.main.post_summary")
    @patch("prime_actions.main.post_review_comments")
    @patch("prime_actions.main.list_pr_files")
    def test_run_no_findings_skips_review_comments(
        self,
        mock_list_files: MagicMock,
        mock_post_comments: MagicMock,
        mock_post_summary: MagicMock,
        github_env: dict[str, str],
    ) -> None:
        mock_list_files.return_value = [
            PRFile(filename="clean.py", patch="@@ -0,0 +1,1 @@\n+x = 1", status="added")
        ]

        with patch.dict(os.environ, github_env, clear=True):
            run()

        mock_post_comments.assert_not_called()
        mock_post_summary.assert_called_once()

    def test_run_exits_on_invalid_timeout(self, github_env: dict[str, str]) -> None:
        github_env["INPUT_TIMEOUT"] = "not_a_number"
        with patch.dict(os.environ, github_env, clear=True), pytest.raises(SystemExit):
            run()
