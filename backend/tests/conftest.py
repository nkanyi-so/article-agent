"""Test-wide isolation.

Set before any app module is imported, so no test can load the developer's `.env`
by constructing settings early. Sockets are blocked by pytest-socket (see pyproject).
"""

import os

os.environ["APP_ENV_FILE"] = ""
