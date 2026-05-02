"""
utils/llm.py
LLM factory — tries providers in order: Bedrock → Anthropic → Gemini.
Falls back transparently at invoke-time so the rest of the codebase is unaware.
"""
import os
from utils.logging import get_logger

log = get_logger(__name__)

# ── Model IDs ─────────────────────────────────────────────────────────────────
_BEDROCK_SONNET = "us.anthropic.claude-sonnet-4-5-20251001-v1:0"
_BEDROCK_HAIKU = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

_ANTHROPIC_SONNET = "claude-sonnet-4-5-20251001"
_ANTHROPIC_HAIKU = "claude-haiku-4-5-20251001"

# Gemini 2.5 models (latest stable)
_GEMINI_SONNET = "gemini-2.5-pro"
_GEMINI_HAIKU = "gemini-2.5-flash"


def _key_is_real(key: str, placeholder_prefixes: tuple) -> bool:
    return bool(key) and not any(key.startswith(p) for p in placeholder_prefixes)


def _bedrock_creds_present() -> bool:
    if os.environ.get("DISABLE_BEDROCK", "").lower() == "true":
        return False
    return bool(os.environ.get("AWS_ACCESS_KEY_ID"))


def _anthropic_key_real() -> bool:
    from config.settings import settings
    return _key_is_real(settings.anthropic_api_key, ("sk-ant-xxx", ""))


def _gemini_key_real() -> bool:
    from config.settings import settings
    return _key_is_real(settings.gemini_api_key, (""))


def _make_bedrock(model: str):
    from langchain_aws import ChatBedrock
    from config.settings import settings
    model_id = _BEDROCK_SONNET if model == "sonnet" else _BEDROCK_HAIKU
    llm = ChatBedrock(
        model_id=model_id,
        region_name=settings.aws_default_region,
        model_kwargs={
            "temperature": 0.1 if model == "sonnet" else 0.0,
            "max_tokens": 4096 if model == "sonnet" else 1024,
        },
    )
    log.info("Bedrock LLM initialised", model=model_id)
    return llm


def _make_anthropic(model: str):
    from langchain_anthropic import ChatAnthropic
    from config.settings import settings
    model_id = _ANTHROPIC_SONNET if model == "sonnet" else _ANTHROPIC_HAIKU
    llm = ChatAnthropic(
        model=model_id,
        api_key=settings.anthropic_api_key,
        temperature=0.1 if model == "sonnet" else 0.0,
        max_tokens=4096 if model == "sonnet" else 1024,
    )
    log.info("Anthropic LLM initialised", model=model_id)
    return llm


def _make_gemini(model: str):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from config.settings import settings
    model_id = _GEMINI_SONNET if model == "sonnet" else _GEMINI_HAIKU
    llm = ChatGoogleGenerativeAI(
        model=model_id,
        google_api_key=settings.gemini_api_key,
        temperature=0.1 if model == "sonnet" else 0.0,
        max_tokens=4096 if model == "sonnet" else 2048,
    )
    log.info("Gemini LLM initialised", model=model_id)
    return llm


class _FallbackLLM:
    """
    Tries Bedrock → Anthropic → Gemini in order.
    First provider that succeeds at invoke-time is pinned for subsequent calls.
    """

    def __init__(self, model: str):
        self._model = model
        self._providers: list = []  # ordered list of (name, client)

        if _bedrock_creds_present():
            try:
                self._providers.append(("bedrock", _make_bedrock(model)))
            except Exception as e:
                log.warning("Bedrock init failed", error=str(e))

        if _anthropic_key_real():
            try:
                self._providers.append(("anthropic", _make_anthropic(model)))
            except Exception as e:
                log.warning("Anthropic init failed", error=str(e))

        if _gemini_key_real():
            try:
                self._providers.append(("gemini", _make_gemini(model)))
            except Exception as e:
                log.warning("Gemini init failed", error=str(e))

        if not self._providers:
            raise RuntimeError(
                "No LLM provider available. Set GEMINI_API_KEY, ANTHROPIC_API_KEY, "
                "or valid AWS Bedrock credentials in .env"
            )

        log.info("LLM ready", model=model,
                 providers=[p[0] for p in self._providers])

    async def ainvoke(self, *args, **kwargs):
        last_err = None
        for name, client in self._providers:
            try:
                result = await client.ainvoke(*args, **kwargs)
                # Pin successful provider to front for next call
                if self._providers[0][0] != name:
                    self._providers = [(n, c) for n, c in self._providers if n == name] + \
                                      [(n, c) for n, c in self._providers if n != name]
                return result
            except Exception as e:
                log.warning(f"{name} ainvoke failed, trying next", error=str(e))
                last_err = e
        raise RuntimeError(f"All LLM providers failed. Last error: {last_err}")

    def invoke(self, *args, **kwargs):
        last_err = None
        for name, client in self._providers:
            try:
                return client.invoke(*args, **kwargs)
            except Exception as e:
                log.warning(f"{name} invoke failed, trying next", error=str(e))
                last_err = e
        raise RuntimeError(f"All LLM providers failed. Last error: {last_err}")


_sonnet: _FallbackLLM | None = None
_haiku: _FallbackLLM | None = None


def get_sonnet() -> _FallbackLLM:
    """Claude Sonnet / Gemini Pro — planning, generation, debate."""
    global _sonnet
    if _sonnet is None:
        _sonnet = _FallbackLLM("sonnet")
    return _sonnet


def get_haiku() -> _FallbackLLM:
    """Claude Haiku / Gemini Flash — extraction, classification, cheap ops."""
    global _haiku
    if _haiku is None:
        _haiku = _FallbackLLM("haiku")
    return _haiku


def get_llm(model: str = "sonnet", provider: str = "bedrock") -> _FallbackLLM:
    """Backwards-compatible alias."""
    return get_sonnet() if model == "sonnet" else get_haiku()
