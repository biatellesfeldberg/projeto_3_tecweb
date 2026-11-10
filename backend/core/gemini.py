"""
Serviço central de comunicação com o Google Gemini.

Todas as chamadas à IA do projeto devem passar por aqui. Assim, a chave
fica só no backend (nunca no frontend) e os erros são tratados de um
jeito único.

Uso básico:

    from core.gemini import generate_text, generate_json

    texto = generate_text("Sugira um passeio em Lisboa.")
    dados = generate_json("Responda em JSON com a chave 'cidade'.")

Os erros levantados aqui herdam de APIException do Django REST Framework.
Se uma view não capturar o erro, o DRF já devolve automaticamente uma
resposta JSON com a mensagem e o status HTTP adequados.
"""

import json
import logging
import time
from functools import lru_cache

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from rest_framework import status
from rest_framework.exceptions import APIException


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Erros do serviço
# ---------------------------------------------------------------------------


class GeminiError(APIException):
    """Erro base de todas as falhas de comunicação com o Gemini."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Não foi possível falar com o assistente de viagens agora."
    default_code = "gemini_error"


class GeminiNotConfiguredError(GeminiError):
    """A chave GEMINI_API_KEY não foi definida no .env."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "O assistente de viagens não está configurado no servidor."
    default_code = "gemini_not_configured"


class GeminiUnavailableError(GeminiError):
    """O Gemini está fora do ar, demorou demais ou houve falha de rede."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = (
        "O assistente de viagens está indisponível no momento. "
        "Tente novamente em alguns instantes."
    )
    default_code = "gemini_unavailable"


class GeminiRateLimitError(GeminiError):
    """O limite de uso da API (cota gratuita) foi atingido."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = (
        "Muitas solicitações ao assistente de viagens. "
        "Aguarde um pouco e tente novamente."
    )
    default_code = "gemini_rate_limited"


class GeminiInvalidResponseError(GeminiError):
    """O Gemini respondeu, mas a resposta veio vazia, bloqueada ou em formato errado."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = (
        "O assistente de viagens devolveu uma resposta inválida. "
        "Tente novamente."
    )
    default_code = "gemini_invalid_response"


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_client(api_key, timeout_seconds):
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
    )


def get_client():
    """Devolve o cliente do Gemini, criado uma única vez."""
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        raise GeminiNotConfiguredError()
    return _build_client(api_key, settings.GEMINI_TIMEOUT_SECONDS)


# ---------------------------------------------------------------------------
# Chamadas
# ---------------------------------------------------------------------------


# Códigos HTTP que indicam falha temporária do lado do Google.
_TEMPORARY_ERROR_CODES = {500, 502, 503, 504}


def _call_gemini(prompt, config):
    """
    Faz a chamada ao Gemini e converte os erros do SDK nos erros do projeto.

    Falhas temporárias (servidor fora do ar, timeout, rede) são tentadas
    novamente algumas vezes antes de desistir. Limite de uso (429) não é
    repetido, para não gastar ainda mais a cota.
    """
    client = get_client()
    max_retries = settings.GEMINI_MAX_RETRIES
    last_error = None

    for attempt in range(max_retries + 1):
        if attempt > 0:
            time.sleep(settings.GEMINI_RETRY_DELAY_SECONDS * attempt)

        try:
            return client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

        except genai_errors.APIError as error:
            if error.code == 429:
                logger.warning("Gemini: limite de uso atingido (%s).", error)
                raise GeminiRateLimitError() from error

            if error.code in _TEMPORARY_ERROR_CODES:
                logger.warning(
                    "Gemini: falha temporária %s (tentativa %s de %s).",
                    error.code,
                    attempt + 1,
                    max_retries + 1,
                )
                last_error = error
                continue

            # 400, 401, 403, 404...: problema na requisição, na chave ou no
            # nome do modelo. Repetir não resolve.
            logger.error("Gemini: erro na requisição: %s", error)
            raise GeminiUnavailableError() from error

        except Exception as error:  # timeout, falha de rede etc.
            logger.warning(
                "Gemini: erro de conexão (tentativa %s de %s): %s",
                attempt + 1,
                max_retries + 1,
                error,
            )
            last_error = error

    raise GeminiUnavailableError() from last_error


def _extract_text(response):
    """Pega o texto da resposta ou levanta erro se ela veio vazia ou bloqueada."""
    try:
        text = response.text
    except Exception as error:
        raise GeminiInvalidResponseError() from error

    if not text or not text.strip():
        reason = None
        if getattr(response, "prompt_feedback", None):
            reason = response.prompt_feedback.block_reason
        logger.warning("Gemini: resposta vazia (motivo do bloqueio: %s).", reason)
        raise GeminiInvalidResponseError()

    return text.strip()


def generate_text(prompt, system_instruction=None, temperature=None):
    """
    Envia um prompt ao Gemini e devolve a resposta em texto.

    - prompt: o que será perguntado.
    - system_instruction: instruções fixas de comportamento (opcional).
    - temperature: criatividade da resposta, de 0 a 2 (opcional).
    """
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )
    response = _call_gemini(prompt, config)
    return _extract_text(response)


def generate_json(
    prompt,
    system_instruction=None,
    schema=None,
    required_keys=None,
    temperature=None,
):
    """
    Envia um prompt ao Gemini pedindo resposta em JSON e devolve o dado já
    convertido para dict/list do Python.

    - schema: JSON Schema opcional descrevendo o formato esperado. Quando
      informado, o Gemini é obrigado a seguir esse formato.
    - required_keys: chaves que precisam existir no objeto devolvido. Se
      faltar alguma, a resposta é considerada inválida.
    """
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json",
        response_json_schema=schema,
    )
    response = _call_gemini(prompt, config)
    text = _extract_text(response)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        logger.warning("Gemini: resposta não é um JSON válido: %s", text[:200])
        raise GeminiInvalidResponseError() from error

    if required_keys:
        if not isinstance(data, dict):
            raise GeminiInvalidResponseError()
        missing = [key for key in required_keys if key not in data]
        if missing:
            logger.warning("Gemini: faltam chaves na resposta: %s", missing)
            raise GeminiInvalidResponseError()

    return data
