"""Router -> RAG assembly -> real LLM HTTP adapter -> transactional persistence.

Only retrieval results and the model's HTTP response are stubbed. JWT handling,
prompt construction, provider parsing, database writes and history reads are real.
"""
import unittest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from apps.backend.api import chat as chat_api
from apps.backend.core import llm
from apps.backend.tests import test_chat_conversation as persistence_tests


class ChatPipelineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = persistence_tests.ChatConversationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.requests = []
        self.answer = "Chùa Thiên Mụ được dựng năm 1601."
        self.finish_reason = "stop"
        self.failure = None
        self.enterContext(patch.object(chat_api, 'generate_response', llm.generate_response))
        self.enterContext(patch.object(chat_api, 'get_generation_details', llm.get_generation_details))
        self.enterContext(patch.object(llm, 'get_model', return_value=(None, None, 'llama_server')))
        self.enterContext(patch.object(llm.httpx, 'post', side_effect=self.respond))

    def respond(self, url, *, json, timeout):
        self.assertTrue(url.endswith('/v1/chat/completions'))
        self.assertGreater(timeout, 0)
        self.assertEqual(json['temperature'], 0)
        self.requests.append(json)
        if self.failure:
            raise self.failure
        return httpx.Response(200, request=httpx.Request('POST', url), json={
            'model': 'integration-llama', 'usage': {'total_tokens': 42},
            'choices': [{'message': {'content': self.answer}, 'finish_reason': self.finish_reason}],
        })

    def test_account_history_restoration_and_continuation_cross_the_provider_boundary(self):
        fixture = self.fixture
        first = fixture.create_conversation(message='Chùa Thiên Mụ xây năm nào?')
        fixture.create_conversation(account_id=2, message='PRIVATE ACCOUNT B QUESTION')
        with TestClient(fixture.client.app) as reconnected:
            listing = reconnected.get('/api/chat/conversations', headers=fixture.headers())
            self.assertEqual([item['id'] for item in listing.json()], [first['conversation_id']])
            path = f'/api/chat/conversations/{first["conversation_id"]}/messages'
            self.assertEqual(reconnected.get(path, headers=fixture.headers(2)).status_code, 403)
            history = reconnected.get(path, headers=fixture.headers()).json()['messages']
            self.assertEqual(history[1]['citations'], first['citations'])
            response = reconnected.post('/api/chat/message', headers=fixture.headers(), json={
                'message': 'Còn kiến trúc?', 'conversation_id': first['conversation_id'], 'scene_context': 'Cổng chính',
            })
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['abstained'])
        sent = self.requests[-1]['messages']
        self.assertEqual([message['role'] for message in sent], ['system', 'user', 'assistant', 'user'])
        self.assertEqual(sent[1]['content'], 'Chùa Thiên Mụ xây năm nào?')
        self.assertEqual(sent[2]['content'], self.answer)
        self.assertIn(fixture.evidence.text, sent[-1]['content'])
        self.assertNotIn('PRIVATE ACCOUNT B QUESTION', str(sent))
        self.assertEqual(fixture.counts(), (2, 6, 3))

    def test_embedded_compatibility_chat_has_context_citations_and_no_persistence_requirement(self):
        response = self.fixture.client.post('/api/chat', json={
            'message': 'Còn kiến trúc?', 'heritage_context': 'Chùa Thiên Mụ', 'scene_context': 'Cổng chính',
            'conversation_context': [
                {'role': 'user', 'content': 'Chùa Thiên Mụ ở đâu?'}, {'role': 'assistant', 'content': 'Huế.'},
            ],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['answer'], self.answer)
        self.assertTrue(response.json()['sources'])
        self.assertFalse(response.json()['needs_user_choice'])
        self.assertFalse(response.json()['abstained'])
        self.assertEqual(len(self.requests[0]['messages']), 4)
        self.assertEqual(self.fixture.counts(), (0, 0, 0))

    def test_empty_or_truncated_inference_is_not_committed_or_returned_as_an_answer(self):
        for text, finish_reason in [('', 'stop'), ('Partial answer', 'length'), ('Filtered', 'content_filter')]:
            with self.subTest(finish_reason=finish_reason):
                self.answer, self.finish_reason = text, finish_reason
                response = self.fixture.client.post('/api/chat/message', headers=self.fixture.headers(), json={'message': 'Question'})
                self.assertEqual(response.status_code, 500)
                self.assertEqual(self.fixture.counts(), (0, 0, 0))
                legacy = self.fixture.client.post('/api/chat', json={'message': 'Question'})
                self.assertEqual(legacy.status_code, 503)

    def test_provider_connection_failure_is_safe_and_atomic_for_both_interfaces(self):
        self.failure = httpx.ConnectError('private-provider-credentials')
        response = self.fixture.client.post('/api/chat/message', headers=self.fixture.headers(), json={'message': 'Question'})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private-provider', response.text)
        self.assertEqual(self.fixture.counts(), (0, 0, 0))
        legacy = self.fixture.client.post('/api/chat', json={'message': 'Question'})
        self.assertEqual(legacy.status_code, 503)
        self.assertNotIn('private-provider', legacy.text)


class ChatStartupTests(unittest.TestCase):
    def test_env_configuration_is_loaded_before_authentication_modules(self):
        code = '''
import os
import dotenv
os.environ.pop('JWT_SECRET_KEY', None)
def configure(*args, **kwargs):
    os.environ['JWT_SECRET_KEY'] = 'isolated-configured-test-secret'
    return True
dotenv.load_dotenv = configure
from apps.backend import app
from apps.backend.core.security import SECRET_KEY
assert SECRET_KEY == 'isolated-configured-test-secret'
'''
        result = subprocess.run(
            [sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[3],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
