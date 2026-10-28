import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class DockerConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(['docker', 'compose', 'config', '--format', 'json'],
                                cwd=ROOT, check=True, capture_output=True, text=True)
        cls.config = json.loads(result.stdout)

    def test_root_compose_does_not_manage_external_service_processes(self):
        # The merged local setup reuses the separate heritagegraph project.
        self.assertEqual(self.config['services'], {})

    def test_root_compose_cannot_create_or_replace_external_database_volumes(self):
        self.assertFalse(self.config.get('volumes'))
        self.assertFalse(self.config.get('networks'))

    def test_docker_context_keeps_business_orm_models(self):
        patterns = (ROOT / '.dockerignore').read_text().splitlines()
        self.assertIn('!apps/backend/models', patterns)
        self.assertIn('!apps/backend/models/*.py', patterns)
