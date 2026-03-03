from __future__ import annotations

from unittest.mock import MagicMock, patch

from prime_actions.commenter import (
    REVIEW_COMMENT_BODY,
    build_summary,
    post_review_comments,
    post_summary,
)
from prime_actions.models import PasswordFinding, PRContext


class TestPostReviewComments:
    @patch("prime_actions.commenter.list_review_comments", return_value=[])
    def test_posts_comment_for_each_finding(
        self, _mock_list: MagicMock, pr_context: PRContext
    ) -> None:
        findings = [
            PasswordFinding(file_path="config.py", line=4, content='DB_PASSWORD = "secret"'),
            PasswordFinding(file_path="auth.py", line=10, content='password = "admin"'),
        ]

        with patch("prime_actions.commenter.create_review_comment") as mock_create:
            posted = post_review_comments(pr_context, findings)

        assert posted == 2
        assert mock_create.call_count == 2
        mock_create.assert_any_call(
            context=pr_context,
            file_path="config.py",
            line=4,
            body=REVIEW_COMMENT_BODY,
        )
        mock_create.assert_any_call(
            context=pr_context,
            file_path="auth.py",
            line=10,
            body=REVIEW_COMMENT_BODY,
        )

    @patch("prime_actions.commenter.list_review_comments", return_value=[])
    def test_empty_findings_posts_nothing(
        self, _mock_list: MagicMock, pr_context: PRContext
    ) -> None:
        with patch("prime_actions.commenter.create_review_comment") as mock_create:
            posted = post_review_comments(pr_context, [])

        assert posted == 0
        mock_create.assert_not_called()

    @patch("prime_actions.commenter.list_review_comments", return_value=[])
    def test_continues_on_api_error(
        self, _mock_list: MagicMock, pr_context: PRContext
    ) -> None:
        findings = [
            PasswordFinding(file_path="a.py", line=1, content="password"),
            PasswordFinding(file_path="b.py", line=2, content="password"),
        ]

        with patch("prime_actions.commenter.create_review_comment") as mock_create:
            mock_create.side_effect = [Exception("API error"), MagicMock()]
            posted = post_review_comments(pr_context, findings)

        assert posted == 1
        assert mock_create.call_count == 2

    @patch("prime_actions.commenter.list_review_comments")
    def test_skips_already_commented_findings(
        self, mock_list: MagicMock, pr_context: PRContext
    ) -> None:
        mock_list.return_value = [
            {"path": "config.py", "line": 4, "body": REVIEW_COMMENT_BODY},
        ]
        findings = [
            PasswordFinding(file_path="config.py", line=4, content='DB_PASSWORD = "secret"'),
            PasswordFinding(file_path="auth.py", line=10, content='password = "admin"'),
        ]

        with patch("prime_actions.commenter.create_review_comment") as mock_create:
            posted = post_review_comments(pr_context, findings)

        assert posted == 1
        mock_create.assert_called_once_with(
            context=pr_context,
            file_path="auth.py",
            line=10,
            body=REVIEW_COMMENT_BODY,
        )

    @patch("prime_actions.commenter.list_review_comments")
    def test_skips_all_when_all_already_commented(
        self, mock_list: MagicMock, pr_context: PRContext
    ) -> None:
        mock_list.return_value = [
            {"path": "config.py", "line": 4, "body": REVIEW_COMMENT_BODY},
            {"path": "auth.py", "line": 10, "body": REVIEW_COMMENT_BODY},
        ]
        findings = [
            PasswordFinding(file_path="config.py", line=4, content='DB_PASSWORD = "secret"'),
            PasswordFinding(file_path="auth.py", line=10, content='password = "admin"'),
        ]

        with patch("prime_actions.commenter.create_review_comment") as mock_create:
            posted = post_review_comments(pr_context, findings)

        assert posted == 0
        mock_create.assert_not_called()

    @patch("prime_actions.commenter.list_review_comments")
    def test_ignores_comments_with_different_body(
        self, mock_list: MagicMock, pr_context: PRContext
    ) -> None:
        mock_list.return_value = [
            {"path": "config.py", "line": 4, "body": "Some other comment"},
        ]
        findings = [
            PasswordFinding(file_path="config.py", line=4, content='DB_PASSWORD = "secret"'),
        ]

        with patch("prime_actions.commenter.create_review_comment") as mock_create:
            posted = post_review_comments(pr_context, findings)

        assert posted == 1
        mock_create.assert_called_once()


class TestBuildSummary:
    def test_summary_contains_counts(self) -> None:
        summary = build_summary(total_lines=150, findings_count=3)
        assert "150" in summary
        assert "3" in summary
        assert "PR Password Scanner Summary" in summary

    def test_summary_is_markdown_table(self) -> None:
        summary = build_summary(total_lines=0, findings_count=0)
        assert "| Metric | Count |" in summary
        assert "| Total added lines in PR | 0 |" in summary
        assert "| Password occurrences found | 0 |" in summary


class TestPostSummary:
    def test_posts_summary_comment(self, pr_context: PRContext) -> None:
        with patch("prime_actions.commenter.create_pr_comment") as mock_create:
            post_summary(pr_context, total_lines=100, findings_count=5)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs["context"] == pr_context
        assert "100" in call_kwargs.kwargs["body"]
        assert "5" in call_kwargs.kwargs["body"]

    def test_handles_api_error_gracefully(self, pr_context: PRContext) -> None:
        with patch("prime_actions.commenter.create_pr_comment") as mock_create:
            mock_create.side_effect = Exception("API error")
            post_summary(pr_context, total_lines=100, findings_count=5)
