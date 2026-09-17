"""Google Gemini API client specialized for GUI code generation."""

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    types = None


@dataclass
class Message:
    """A single message in a conversation."""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Conversation:
    """A conversation thread for iterative GUI building."""
    title: str = "Untitled"
    messages: list[Message] = field(default_factory=list)
    system_instruction: str = ""
    framework: str = "customtkinter"

    def to_contents(self) -> list:
        """Convert to Gemini API content format."""
        if not types:
            return []
        contents = []
        for msg in self.messages:
            contents.append(types.Content(
                role=msg.role,
                parts=[types.Part.from_text(text=msg.content)],
            ))
        return contents

    def add_user(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))

    def add_model(self, content: str) -> None:
        self.messages.append(Message(role="model", content=content))

    def clear(self) -> None:
        self.messages.clear()

    def to_dict(self) -> dict:
        """Serialize for saving."""
        return {
            "title": self.title,
            "framework": self.framework,
            "system_instruction": self.system_instruction,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in self.messages
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """Deserialize from saved data."""
        conv = cls(
            title=data.get("title", "Untitled"),
            framework=data.get("framework", "customtkinter"),
            system_instruction=data.get("system_instruction", ""),
        )
        for m in data.get("messages", []):
            conv.messages.append(Message(
                role=m["role"],
                content=m["content"],
                timestamp=m.get("timestamp", time.time()),
            ))
        return conv


class GUIGeminiClient:
    """Thread-safe Gemini client optimized for GUI generation tasks."""

    MAX_RETRIES = 5
    BASE_DELAY = 1.0

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "gemini-2.5-flash-preview-04-17",
        max_tokens: int = 65536,
        temperature: float = 0.7,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client = None
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._configured = False
        if api_key:
            self.configure(api_key)

    @property
    def is_configured(self) -> bool:
        return self._configured and GEMINI_AVAILABLE

    @property
    def model_name(self) -> str:
        return self._model_name

    def configure(self, api_key: str) -> bool:
        """Configure with API key."""
        if not GEMINI_AVAILABLE:
            logger.error("google-genai package not installed")
            return False
        try:
            self._client = genai.Client(api_key=api_key)
            self._api_key = api_key
            self._configured = True
            logger.info("Gemini client configured: %s", self._model_name)
            return True
        except Exception as exc:
            logger.error("Failed to configure Gemini: %s", exc)
            self._configured = False
            return False

    def update_settings(
        self,
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> None:
        """Update generation settings."""
        if model_name:
            self._model_name = model_name
        if max_tokens is not None:
            self._max_tokens = max_tokens
        if temperature is not None:
            self._temperature = temperature

    def cancel(self) -> None:
        """Signal cancellation of current generation."""
        self._cancel_event.set()

    def generate(
        self,
        prompt: str,
        conversation: Optional[Conversation] = None,
        system_instruction: str = "",
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Generate GUI code with retry logic. Returns full response text."""
        self._cancel_event.clear()
        if not self.is_configured:
            raise RuntimeError("Gemini client not configured. Set your API key.")
        with self._lock:
            return self._generate_with_retry(
                prompt, conversation, system_instruction, on_progress,
            )

    def _generate_with_retry(
        self,
        prompt: str,
        conversation: Optional[Conversation],
        system_instruction: str,
        on_progress: Optional[Callable[[str], None]],
    ) -> str:
        """Generate with exponential backoff retry."""
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            if self._cancel_event.is_set():
                raise InterruptedError("Generation cancelled")
            try:
                config = types.GenerateContentConfig(
                    max_output_tokens=self._max_tokens,
                    temperature=self._temperature,
                )
                if system_instruction:
                    config.system_instruction = system_instruction

                contents = []
                if conversation and conversation.messages:
                    contents = conversation.to_contents()
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ))

                full_text = ""
                for chunk in self._client.models.generate_content_stream(
                    model=self._model_name,
                    contents=contents,
                    config=config,
                ):
                    if self._cancel_event.is_set():
                        raise InterruptedError("Generation cancelled")
                    if chunk.text:
                        full_text += chunk.text
                        if on_progress:
                            on_progress(full_text)

                if conversation:
                    conversation.add_user(prompt)
                    conversation.add_model(full_text)

                return full_text

            except InterruptedError:
                raise
            except Exception as exc:
                last_error = exc
                error_str = str(exc).lower()
                if any(k in error_str for k in ("429", "quota", "resource_exhausted")):
                    delay = self.BASE_DELAY * (2 ** attempt)
                    logger.warning("Rate limited (attempt %d/%d), retry in %.1fs",
                                   attempt + 1, self.MAX_RETRIES, delay)
                    time.sleep(delay)
                elif any(k in error_str for k in ("api key", "unauthorized", "invalid")):
                    raise RuntimeError(f"API key error: {exc}") from exc
                else:
                    delay = self.BASE_DELAY * (2 ** attempt)
                    logger.warning("Error (attempt %d/%d), retry in %.1fs: %s",
                                   attempt + 1, self.MAX_RETRIES, delay, exc)
                    time.sleep(delay)

        raise RuntimeError(f"Failed after {self.MAX_RETRIES} attempts: {last_error}")

    def generate_gui(
        self,
        description: str,
        framework: str = "customtkinter",
        style: str = "modern",
        components: Optional[list[str]] = None,
        existing_code: Optional[str] = None,
        conversation: Optional[Conversation] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> str:
        """High-level GUI generation with structured prompt building."""
        from .prompt_engine import build_generation_prompt, get_system_instruction
        prompt = build_generation_prompt(
            description=description,
            framework=framework,
            style=style,
            components=components,
            existing_code=existing_code,
        )
        system_inst = get_system_instruction(framework)
        return self.generate(
            prompt=prompt,
            conversation=conversation,
            system_instruction=system_inst,
            on_progress=on_progress,
        )

    def refine_gui(
        self,
        feedback: str,
        current_code: str,
        framework: str = "customtkinter",
        conversation: Optional[Conversation] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Refine existing GUI code based on user feedback."""
        from .prompt_engine import build_refinement_prompt, get_system_instruction
        prompt = build_refinement_prompt(
            feedback=feedback,
            current_code=current_code,
            framework=framework,
        )
        system_inst = get_system_instruction(framework)
        return self.generate(
            prompt=prompt,
            conversation=conversation,
            system_instruction=system_inst,
            on_progress=on_progress,
        )

    def add_component(
        self,
        component_type: str,
        current_code: str,
        placement: str = "",
        framework: str = "customtkinter",
        conversation: Optional[Conversation] = None,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Add a specific component to existing GUI code."""
        from .prompt_engine import build_component_prompt, get_system_instruction
        prompt = build_component_prompt(
            component_type=component_type,
            current_code=current_code,
            placement=placement,
            framework=framework,
        )
        system_inst = get_system_instruction(framework)
        return self.generate(
            prompt=prompt,
            conversation=conversation,
            system_instruction=system_inst,
            on_progress=on_progress,
        )

    def test_connection(self) -> tuple[bool, str]:
        """Test API connectivity."""
        if not GEMINI_AVAILABLE:
            return False, "google-genai not installed. Run: uv pip install google-genai"
        if not self._api_key:
            return False, "No API key configured"
        try:
            self.configure(self._api_key)
            response = self._client.models.generate_content(
                model=self._model_name,
                contents="Say 'OK' and nothing else.",
            )
            if response.text:
                return True, f"Connected to {self._model_name}"
            return False, "Empty response"
        except Exception as exc:
            return False, f"Connection failed: {exc}"

    def list_models(self) -> list[str]:
        """List available Gemini models."""
        if not self.is_configured:
            return []
        try:
            models = self._client.models.list()
            return [
                m.name.replace("models/", "")
                for m in models
                if hasattr(m, "name")
            ]
        except Exception as exc:
            logger.error("Failed to list models: %s", exc)
            return []
