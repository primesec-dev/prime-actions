from __future__ import annotations

import pytest

from prime_actions.models import PRContext, PRFile


@pytest.fixture()
def pr_context() -> PRContext:
    return PRContext(
        owner="test-owner",
        repo="test-repo",
        pr_number=42,
        head_sha="abc123def456",
        token="ghp_test_token_123",
    )


PATCH_SINGLE_PASSWORD = """\
@@ -0,0 +1,5 @@
+import os
+
+DB_HOST = "localhost"
+DB_PASSWORD = "secret123"
+DB_PORT = 5432"""

PATCH_MULTIPLE_PASSWORDS = """\
@@ -0,0 +1,4 @@
+password = "admin"
+username = "root"
+PASSWORD = "ADMIN"
+user_password = "changeme" """

PATCH_NO_PASSWORD = """\
@@ -0,0 +1,3 @@
+import os
+
+DB_HOST = "localhost" """

PATCH_PASSWORD_IN_CONTEXT_ONLY = """\
@@ -5,7 +5,7 @@
 import os

 DB_HOST = "localhost"
-DB_PASSWORD = "old_secret"
+DB_SECRET = "new_secret"
 DB_PORT = 5432"""

PATCH_MULTIPLE_HUNKS = """\
@@ -1,3 +1,4 @@
 import os
+import sys

 DB_HOST = "localhost"
@@ -10,3 +11,4 @@

 def connect():
     pass
+    password = get_password()"""

PATCH_MIXED_CASE = """\
@@ -0,0 +1,3 @@
+Password = "mixed"
+pAsSwOrD = "weird"
+no_match = "safe" """


@pytest.fixture()
def pr_file_single_password() -> PRFile:
    return PRFile(filename="config.py", patch=PATCH_SINGLE_PASSWORD, status="added")


@pytest.fixture()
def pr_file_multiple_passwords() -> PRFile:
    return PRFile(filename="settings.py", patch=PATCH_MULTIPLE_PASSWORDS, status="added")


@pytest.fixture()
def pr_file_no_password() -> PRFile:
    return PRFile(filename="utils.py", patch=PATCH_NO_PASSWORD, status="added")


@pytest.fixture()
def pr_file_binary() -> PRFile:
    return PRFile(filename="image.png", patch=None, status="added")


@pytest.fixture()
def pr_file_password_in_context_only() -> PRFile:
    return PRFile(filename="config.py", patch=PATCH_PASSWORD_IN_CONTEXT_ONLY, status="modified")


@pytest.fixture()
def pr_file_multiple_hunks() -> PRFile:
    return PRFile(filename="app.py", patch=PATCH_MULTIPLE_HUNKS, status="modified")


@pytest.fixture()
def pr_file_mixed_case() -> PRFile:
    return PRFile(filename="auth.py", patch=PATCH_MIXED_CASE, status="added")
