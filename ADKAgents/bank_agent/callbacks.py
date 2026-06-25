from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

IDENTITY_VERIFIED_KEY = "identity_verified"


def require_verified_identity(callback_context: CallbackContext) -> LlmResponse | None:
    """Skips the agent if identity verification has not been passed."""
    if not callback_context.state.get(IDENTITY_VERIFIED_KEY, False):
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="Identity verification failed or was not completed. Cannot proceed.")],
            )
        )
    return None
