from unittest.mock import MagicMock, patch

import httpx
from django.test import SimpleTestCase, override_settings
from google.genai import errors as genai_errors

from core import gemini
from core.gemini import (
    GeminiInvalidResponseError,
    GeminiNotConfiguredError,
    GeminiRateLimitError,
    GeminiUnavailableError,
    generate_json,
    generate_text,
)


def fake_response(text):
    response = MagicMock()
    response.text = text
    response.prompt_feedback = None
    return response


def api_error(code):
    return genai_errors.APIError(code, {"error": {"message": "erro de teste"}})


GEMINI_TEST_SETTINGS = {
    "GEMINI_API_KEY": "chave-de-teste",
    "GEMINI_MODEL": "modelo-de-teste",
    "GEMINI_TIMEOUT_SECONDS": 5,
    "GEMINI_MAX_RETRIES": 2,
    "GEMINI_RETRY_DELAY_SECONDS": 0,
}


@override_settings(**GEMINI_TEST_SETTINGS)
class GeminiServiceTests(SimpleTestCase):
    """Os testes usam um cliente falso: nenhuma chamada real é feita ao Gemini."""

    def setUp(self):
        self.client = MagicMock()
        patcher = patch.object(gemini, "get_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.generate = self.client.models.generate_content

    def test_generate_text_returns_text(self):
        self.generate.return_value = fake_response("  Visite Alfama.  ")

        self.assertEqual(generate_text("Sugira um passeio"), "Visite Alfama.")
        kwargs = self.generate.call_args.kwargs
        self.assertEqual(kwargs["model"], "modelo-de-teste")
        self.assertEqual(kwargs["contents"], "Sugira um passeio")

    def test_generate_json_returns_parsed_data(self):
        self.generate.return_value = fake_response('{"cidade": "Lisboa", "dias": 7}')

        data = generate_json("Responda em JSON", required_keys=["cidade"])

        self.assertEqual(data, {"cidade": "Lisboa", "dias": 7})
        config = self.generate.call_args.kwargs["config"]
        self.assertEqual(config.response_mime_type, "application/json")

    def test_rate_limit_is_not_retried(self):
        self.generate.side_effect = api_error(429)

        with self.assertRaises(GeminiRateLimitError) as ctx:
            generate_text("Oi")

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(self.generate.call_count, 1)

    def test_temporary_error_is_retried_and_can_recover(self):
        self.generate.side_effect = [api_error(503), fake_response("Funcionou")]

        self.assertEqual(generate_text("Oi"), "Funcionou")
        self.assertEqual(self.generate.call_count, 2)

    def test_service_unavailable_after_all_retries(self):
        self.generate.side_effect = api_error(503)

        with self.assertRaises(GeminiUnavailableError) as ctx:
            generate_text("Oi")

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(self.generate.call_count, 3)  # 1 tentativa + 2 repetições

    def test_timeout_is_treated_as_unavailable(self):
        self.generate.side_effect = httpx.ReadTimeout("demorou demais")

        with self.assertRaises(GeminiUnavailableError):
            generate_text("Oi")
        self.assertEqual(self.generate.call_count, 3)

    def test_invalid_key_is_not_retried(self):
        self.generate.side_effect = api_error(400)

        with self.assertRaises(GeminiUnavailableError):
            generate_text("Oi")
        self.assertEqual(self.generate.call_count, 1)

    def test_empty_response_is_invalid(self):
        self.generate.return_value = fake_response("")

        with self.assertRaises(GeminiInvalidResponseError) as ctx:
            generate_text("Oi")
        self.assertEqual(ctx.exception.status_code, 502)

    def test_non_json_response_is_invalid(self):
        self.generate.return_value = fake_response("Isto não é JSON")

        with self.assertRaises(GeminiInvalidResponseError):
            generate_json("Responda em JSON")

    def test_json_missing_required_keys_is_invalid(self):
        self.generate.return_value = fake_response('{"cidade": "Lisboa"}')

        with self.assertRaises(GeminiInvalidResponseError):
            generate_json("Responda em JSON", required_keys=["cidade", "dias"])


class GeminiConfigurationTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="")
    def test_missing_api_key_raises_not_configured(self):
        with self.assertRaises(GeminiNotConfiguredError) as ctx:
            generate_text("Oi")
        self.assertEqual(ctx.exception.status_code, 503)
