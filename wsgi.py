"""
WSGI-точка для Beget (Passenger).

У многих хостинговой платформы ожидается, что в wsgi.py будет переменная
`application` (стандартный WSGI name).
"""

from __future__ import annotations

import sys
from pathlib import Path

project_home = str(Path(__file__).resolve().parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application  # noqa: E402

