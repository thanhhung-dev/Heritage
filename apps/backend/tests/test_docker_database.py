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

    def test_only_opensearch_runs_in_docker(self):
        self.assertEqual(set(self.config['services']), {'opensearch'})

    def test_local_search_is_loopback_bound_persistent_and_resource_limited(self):
        service = self.config['services']['opensearch']
        self.assertEqual(service['ports'][0]['host_ip'], '127.0.0.1')
        self.assertEqual(service['ports'][0]['target'], 9200)
        self.assertEqual(service['volumes'][0]['target'], '/usr/share/opensearch/data')
        self.assertIn('opensearch_data', self.config['volumes'])
        self.assertLessEqual(int(service['mem_limit']), 2 * 1024 ** 3)

    def test_docker_context_keeps_business_orm_models(self):
        patterns = (ROOT / '.dockerignore').read_text().splitlines()
        self.assertIn('!apps/backend/models', patterns)
        self.assertIn('!apps/backend/models/*.py', patterns)
