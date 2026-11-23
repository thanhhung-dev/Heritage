"""Verify env configuration reaches auth before module-level JWT initialization."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class AuthBootstrapTests(unittest.TestCase):
    def test_env_is_loaded_before_security_import_without_starting_services(self):
        script = """
import os
from unittest.mock import patch
def load_env(*args, **kwargs):
    os.environ['JWT_SECRET_KEY'] = 'synthetic-bootstrap-test-key-1234567890'
with patch('dotenv.load_dotenv', side_effect=load_env):
    from apps.backend import app
    from apps.backend.core import security
    assert security.SECRET_KEY == 'synthetic-bootstrap-test-key-1234567890'
    assert app.app.title == 'Heritage'
print('Auth config loaded before security; no lifespan started')
"""
        env = dict(os.environ)
        env.pop("JWT_SECRET_KEY", None)
        result = subprocess.run([sys.executable, "-X", "utf8", "-c", script],
                                cwd=Path(__file__).resolve().parents[3], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
