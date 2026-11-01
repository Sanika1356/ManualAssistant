"""
The only file that talks to the language model.

If the organisers provide a different model or provider, change generate()
and keep its inputs and output the same. Nothing else needs to be touched.
"""
import os

from django.conf import settings


class LLMUnavailable(Exception):
    """Raised when the language model cannot be reached or is not set up."""


def generate(system_prompt, user_prompt):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMUnavailable("ANTHROPIC_API_KEY is missing from the .env file.")

    import anthropic

    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 30),
    )

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
