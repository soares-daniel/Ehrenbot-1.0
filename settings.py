# pylint: disable=wildcard-import, unused-wildcard-import
import os
from pathlib import Path

from dotenv import load_dotenv

DEBUG = os.getenv('DEBUG')
if DEBUG:
    print("------")
    print("DEBUG mode is enabled")
    env_path = Path(".") / ".env.debug"
    load_dotenv(dotenv_path=env_path)
    from settings_files.development import *
else:
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)
    from settings_files.production import *
