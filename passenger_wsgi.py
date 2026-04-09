# -*- coding: utf-8 -*-
"""
WSGI-точка для Beget (Passenger).

Passenger импортирует переменную `application` из этого файла.
"""

import sys
from pathlib import Path


project_home = str(Path(__file__).resolve().parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

try:
    import site

    usersite = site.getusersitepackages()
    if usersite and usersite not in sys.path:
        sys.path.insert(0, usersite)
except Exception:
    # Если по какой-то причине site.getusersitepackages() недоступен,
    # проект все равно попробует импортироваться из стандартных путей.
    pass

from app import app as application  # noqa: E402

