"""
AEGIS LLM Module.

Provides a centralized LLM instance via LangChain.
Swap model/provider by changing LLM_PROVIDER and LLM_MODEL in .env.
"""

from langchain_groq import ChatGroq
from app.config import get_settings


def get_llm():
    """
    Return a LangChain chat model based on the configured provider.

    Currently supports:
      - groq: Uses ChatGroq with the Groq API

    To add new providers, add a new branch here and install
    the corresponding langchain-<provider> package.
    """
    settings = get_settings()

    if settings.llm_provider == "groq":
        return ChatGroq(
            model=settings.llm_model,
            api_key=settings.groq_api_key,
            temperature=0.7,
            max_tokens=4096,
        )
    else:
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}. "
            f"Supported: groq"
        )
