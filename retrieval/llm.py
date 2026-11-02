"""
The only file that talks to the language model.

LLM_PROVIDER in .env chooses the service: "groq" (the default, free plan) or
"anthropic". To add another provider, add a function here with the same inputs
and output. Nothing else needs to be touched.
"""
import os

from django.conf import settings

GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_OUTPUT_TOKENS = 1500


class LLMUnavailable(Exception):
    """Raised when the language model cannot be reached or is not set up."""


def _timeout():
    return getattr(settings, "LLM_TIMEOUT_SECONDS", 30)


def _generate_groq(system_prompt, user_prompt):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LLMUnavailable("GROQ_API_KEY is missing from the .env file.")

    import groq

    # The free plan allows few tokens per minute. When Groq says "too many
    # requests", the client waits the time Groq asks for and tries again.
    client = groq.Groq(api_key=api_key, timeout=_timeout(), max_retries=4)

    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", GROQ_DEFAULT_MODEL),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # A low temperature keeps answers close to the passages.
            temperature=0,
            max_completion_tokens=MAX_OUTPUT_TOKENS,
            reasoning_effort="medium",
            include_reasoning=False,
        )
    except groq.APIError as error:
        raise LLMUnavailable(f"The AI service failed: {error}") from error

    return (response.choices[0].message.content or "").strip()


def _generate_anthropic(system_prompt, user_prompt):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMUnavailable("ANTHROPIC_API_KEY is missing from the .env file.")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key, timeout=_timeout())

    try:
        response = client.messages.create(
            model=getattr(settings, "LLM_MODEL", "claude-haiku-5-5"),
            max_tokens=700,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as error:
        raise LLMUnavailable(f"The AI service failed: {error}") from error

    return "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()


def generate(system_prompt, user_prompt):
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()

    if provider == "groq":
        return _generate_groq(system_prompt, user_prompt)
    if provider == "anthropic":
        return _generate_anthropic(system_prompt, user_prompt)
    raise LLMUnavailable(f"Unknown LLM_PROVIDER in .env: {provider}")
