import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import main_agent as agent


class CanvasTests(unittest.TestCase):
    def test_groq_request_budget(self):
        with patch.object(agent.requests, 'post') as post:
            post.return_value.status_code = 200
            for model in ['openai/gpt-oss-120b', 'openai/gpt-oss-20b']:
                agent.call_openai_style('https://api.groq.com/openai/v1/chat/completions', 'test', model, 'prompt', True)
                self.assertEqual(post.call_args.kwargs['json']['max_tokens'], 3500)

    def test_503_breaker_per_model_and_no_429_count(self):
        with patch('google.genai.Client') as client, patch.object(agent, 'GEMINI_KEYS', list('abcde')), \
                patch.object(agent, 'GEMINI_MODELS', ['gemini-3.8-flash', 'gemini-3.6-flash']), \
                patch.object(agent, 'BACKUP_PROVIDERS', []), patch.dict(agent._COOLDOWN, clear=True), \
                patch.object(agent.time, 'sleep') as sleep:
            generate = client.return_value.models.generate_content
            generate.side_effect = [RuntimeError(msg) for msg in ['503', '429', '503', '503']] + [Mock(text='ok')]
            sources = agent.llm_callers(raw=True)
            calls = iter(sources)
            for message in ['503', '429', '503', '503']:
                with self.assertRaisesRegex(RuntimeError, message):
                    next(calls)[1]('prompt')
            name, call = next(calls)
            self.assertEqual(name, 'Gemini gemini-3.6-flash #1')
            self.assertEqual(call('prompt'), 'ok')
            self.assertEqual(next(iter(sources))[0], name)
            self.assertEqual(generate.call_count, 5)
            self.assertEqual(client.call_args.kwargs['http_options'].timeout, 240000)
            self.assertEqual(generate.call_args.kwargs['config'].thinking_config.thinking_level, 'LOW')
            sleep.assert_not_called()


class ResumeTests(unittest.TestCase):
    def test_resume_after_tts_failure_then_render_failure(self):
        data = dict(title='topik', theme_index=0, scenes=[dict(start=0, end=1, narration='kata')])
        words = [dict(word='kata', start=0, end=1)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(agent, 'PUBLIC_DIR', tmp), \
                patch.object(agent, 'SESSION_PATH', Path(tmp) / 'last_session.json'), \
                patch.object(agent, 'research_and_write', return_value=data) as research, \
                patch.object(agent, 'generate_voices', new_callable=AsyncMock) as tts:
            tts.side_effect = [RuntimeError('TTS'), (words, 1, 'voice.wav')]
            with self.assertRaisesRegex(RuntimeError, 'TTS'):
                agent.prepare_session(False, None)
            self.assertNotIn('voice', json.loads(agent.SESSION_PATH.read_text()))
            audio = Path(tmp) / 'voice.wav'
            audio.write_bytes(b'voice')
            session = agent.prepare_session(True, None)
            self.assertEqual(agent.prepare_session(True, None), session)
            self.assertEqual(session[1]['clip_plan'][0]['durationInFrames'], 30)
            audio.unlink()
            with self.assertRaisesRegex(RuntimeError, 'Checkpoint/audio'):
                agent.prepare_session(True, None)
            research.assert_called_once()
            self.assertEqual(tts.await_count, 2)


if __name__ == '__main__':
    unittest.main()
