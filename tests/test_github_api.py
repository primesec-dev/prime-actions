from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from prime_actions.github_api import (
    InsufficientPermissionsError,
    create_pr_comment,
    create_review_comment,
    list_pr_comments,
    list_pr_files,
    list_review_comments,
    update_pr_comment,
    verify_pr_write_permission,
)
from prime_actions.models import PRContext


@pytest.fixture()
def pr_context() -> PRContext:
    return PRContext(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        head_sha="abc123",
        token="ghp_test",
    )


class TestListPRFiles:
    @patch("prime_actions.github_api.requests.get")
    def test_lists_files_single_page(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"filename": "a.py", "patch": "@@ +1 @@\n+x=1", "status": "added"},
            {"filename": "b.py", "status": "removed"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        files = list_pr_files(pr_context)

        assert len(files) == 2
        assert files[0].filename == "a.py"
        assert files[0].patch == "@@ +1 @@\n+x=1"
        assert files[1].filename == "b.py"
        assert files[1].patch is None

    @patch("prime_actions.github_api.requests.get")
    def test_handles_pagination(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        page1 = [{"filename": f"f{i}.py", "status": "added"} for i in range(100)]
        page2 = [{"filename": "last.py", "status": "added"}]

        resp1 = MagicMock()
        resp1.json.return_value = page1
        resp1.raise_for_status = MagicMock()

        resp2 = MagicMock()
        resp2.json.return_value = page2
        resp2.raise_for_status = MagicMock()

        mock_get.side_effect = [resp1, resp2]

        files = list_pr_files(pr_context)
        assert len(files) == 101
        assert mock_get.call_count == 2

    @patch("prime_actions.github_api.requests.get")
    def test_empty_pr(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        files = list_pr_files(pr_context)
        assert files == []


class TestVerifyPrWritePermission:
    @patch("prime_actions.github_api.requests.post")
    def test_raises_on_403(self, mock_post: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_post.return_value = mock_response

        with pytest.raises(InsufficientPermissionsError, match="pull-requests: write"):
            verify_pr_write_permission(pr_context)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "/pulls/42/comments" in call_kwargs.args[0]
        assert call_kwargs.kwargs["json"] == {}

    @patch("prime_actions.github_api.requests.post")
    def test_passes_on_422(self, mock_post: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_post.return_value = mock_response

        verify_pr_write_permission(pr_context)


class TestListReviewComments:
    @patch("prime_actions.github_api.requests.get")
    def test_lists_comments_single_page(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"path": "config.py", "line": 4, "body": "Remove it please"},
            {"path": "auth.py", "line": 10, "body": "Another comment"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        comments = list_review_comments(pr_context)

        assert len(comments) == 2
        assert comments[0]["path"] == "config.py"
        assert comments[1]["body"] == "Another comment"
        mock_get.assert_called_once()
        assert "/pulls/42/comments" in mock_get.call_args.args[0]

    @patch("prime_actions.github_api.requests.get")
    def test_handles_pagination(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        page1 = [{"path": f"f{i}.py", "line": i, "body": "x"} for i in range(100)]
        page2 = [{"path": "last.py", "line": 1, "body": "x"}]

        resp1 = MagicMock()
        resp1.json.return_value = page1
        resp1.raise_for_status = MagicMock()

        resp2 = MagicMock()
        resp2.json.return_value = page2
        resp2.raise_for_status = MagicMock()

        mock_get.side_effect = [resp1, resp2]

        comments = list_review_comments(pr_context)
        assert len(comments) == 101
        assert mock_get.call_count == 2

    @patch("prime_actions.github_api.requests.get")
    def test_empty_comments(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        comments = list_review_comments(pr_context)
        assert comments == []


class TestCreateReviewComment:
    @patch("prime_actions.github_api.requests.post")
    def test_posts_correct_payload(self, mock_post: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        create_review_comment(pr_context, "config.py", 10, "Remove it please")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "/pulls/42/comments" in call_kwargs.args[0]
        payload = call_kwargs.kwargs["json"]
        assert payload["body"] == "Remove it please"
        assert payload["path"] == "config.py"
        assert payload["line"] == 10
        assert payload["commit_id"] == "abc123"
        assert payload["side"] == "RIGHT"


class TestCreatePRComment:
    @patch("prime_actions.github_api.requests.post")
    def test_posts_summary_comment(self, mock_post: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        create_pr_comment(pr_context, "Summary text")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "/issues/42/comments" in call_kwargs.args[0]
        assert call_kwargs.kwargs["json"]["body"] == "Summary text"


class TestListPRComments:
    @patch("prime_actions.github_api.requests.get")
    def test_lists_comments_single_page(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "body": "hello"},
            {"id": 2, "body": "world"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        comments = list_pr_comments(pr_context)

        assert len(comments) == 2
        assert comments[0]["body"] == "hello"
        mock_get.assert_called_once()
        assert "/issues/42/comments" in mock_get.call_args.args[0]

    @patch("prime_actions.github_api.requests.get")
    def test_handles_pagination(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        page1 = [{"id": i, "body": "x"} for i in range(100)]
        page2 = [{"id": 999, "body": "last"}]

        resp1 = MagicMock()
        resp1.json.return_value = page1
        resp1.raise_for_status = MagicMock()

        resp2 = MagicMock()
        resp2.json.return_value = page2
        resp2.raise_for_status = MagicMock()

        mock_get.side_effect = [resp1, resp2]

        comments = list_pr_comments(pr_context)
        assert len(comments) == 101
        assert mock_get.call_count == 2

    @patch("prime_actions.github_api.requests.get")
    def test_empty_comments(self, mock_get: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        comments = list_pr_comments(pr_context)
        assert comments == []


class TestUpdatePRComment:
    @patch("prime_actions.github_api.requests.patch")
    def test_sends_correct_payload(self, mock_patch: MagicMock, pr_context: PRContext) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_patch.return_value = mock_response

        update_pr_comment(pr_context, comment_id=999, body="Updated body")

        mock_patch.assert_called_once()
        call_kwargs = mock_patch.call_args
        assert "/issues/comments/999" in call_kwargs.args[0]
        assert call_kwargs.kwargs["json"]["body"] == "Updated body"
