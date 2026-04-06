"""
Vision LLM integration via OpenRouter.
Analyzes screenshots to identify screens, elements, and decide actions.
"""

import json
import logging
from typing import Any, Optional

import httpx

from .utils import Config, image_to_base64, resize_screenshot

logger = logging.getLogger("explorer.vision")

# ── Prompts ──────────────────────────────────────────────────────────

SCREEN_ANALYSIS_PROMPT = """You are an expert mobile UI analyst. Analyze this screenshot of a mobile app screen.

You ALSO have the accessibility tree data below (if available) to help identify elements accurately.

**Accessibility Tree:**
{accessibility_tree}

**Instructions:**
1. Give this screen a short, descriptive name (e.g., "Login Screen", "Product List", "Settings")
2. Categorize the screen type (e.g., "authentication", "list", "detail", "settings", "navigation", "form", "modal", "error")
3. Describe what you see in 1-2 sentences
4. List ALL interactive elements you can identify, ordered by their Y position (top to bottom)

For each interactive element, provide:
- A unique ID like "el_1", "el_2", etc.
- The element type: "button", "text_input", "link", "toggle", "checkbox", "tab", "menu_item", "card", "icon_button", "dropdown", "back_button", "nav_item"
- A short label describing what it does
- Estimated center coordinates (x, y) based on the image dimensions
- Priority: "high" (primary actions, navigation), "medium" (secondary actions), "low" (minor/decorative)

Respond with ONLY valid JSON in this exact format:
{{
  "screen_name": "Screen Name",
  "screen_type": "type",
  "description": "What this screen shows",
  "interactive_elements": [
    {{
      "id": "el_1",
      "type": "button",
      "label": "Sign In",
      "x": 200,
      "y": 450,
      "priority": "high"
    }}
  ]
}}"""

SCREEN_COMPARISON_PROMPT = """Compare these two mobile app screenshots and determine if they show the SAME screen or DIFFERENT screens.

Consider:
- Same layout but different content (e.g., scrolled) = SAME screen
- Same screen with a modal/popup overlay = DIFFERENT screen 
- Different layouts entirely = DIFFERENT screen
- Same screen with minor state changes (loading indicators, etc.) = SAME screen

Respond with ONLY valid JSON:
{{
  "is_same_screen": true/false,
  "similarity": 0.0 to 1.0,
  "reason": "Brief explanation"
}}"""


class VisionAnalyzer:
    """Analyzes mobile screenshots using a vision LLM via OpenRouter."""

    def __init__(self, config: Config):
        self.config = config
        self.api_base = config.vision.get("api_base", "https://openrouter.ai/api/v1")
        self.model = config.vision.get("model", "google/gemini-2.0-flash-001")
        self.max_tokens = config.vision.get("max_tokens", 2048)
        self.temperature = config.vision.get("temperature", 0.1)
        self.max_screenshot_size = config.vision.get("screenshot_max_size", 1024)
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://react-native-explorer.local",
                "X-Title": "React Native Explorer Agent",
            },
        )
        self._request_count = 0
        self._total_tokens = 0

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def _chat_completion(
        self, messages: list[dict], max_tokens: int = None
    ) -> str:
        """Send a chat completion request to OpenRouter."""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await self._client.post(
                f"{self.api_base}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            self._request_count += 1
            usage = data.get("usage", {})
            self._total_tokens += usage.get("total_tokens", 0)

            choice = data["choices"][0]
            return choice["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Vision API request failed: {e}")
            raise

    async def analyze_screen(
        self, screenshot_bytes: bytes, accessibility_tree: str = ""
    ) -> dict:
        """
        Analyze a screenshot to identify the screen and interactive elements.
        
        Returns:
            dict with screen_name, screen_type, description, interactive_elements
        """
        # Resize for efficiency
        resized = resize_screenshot(screenshot_bytes, self.max_screenshot_size)
        image_b64 = image_to_base64(resized)

        prompt = SCREEN_ANALYSIS_PROMPT.format(
            accessibility_tree=accessibility_tree if accessibility_tree else "Not available"
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_b64},
                    },
                ],
            }
        ]

        try:
            response_text = await self._chat_completion(messages)
            result = self._parse_json_response(response_text)

            # Validate structure
            if "screen_name" not in result:
                result["screen_name"] = "Unknown Screen"
            if "screen_type" not in result:
                result["screen_type"] = "unknown"
            if "description" not in result:
                result["description"] = ""
            if "interactive_elements" not in result:
                result["interactive_elements"] = []

            logger.info(
                f"🔍 Analyzed screen: [explore]{result['screen_name']}[/explore] "
                f"({len(result['interactive_elements'])} elements)",
                extra={"markup": True},
            )
            return result

        except Exception as e:
            logger.error(f"Screen analysis failed: {e}")
            return {
                "screen_name": "Analysis Failed",
                "screen_type": "error",
                "description": str(e),
                "interactive_elements": [],
            }

    async def compare_screens(
        self, screenshot_a: bytes, screenshot_b: bytes
    ) -> dict:
        """
        Compare two screenshots to determine if they show the same screen.
        
        Returns:
            dict with is_same_screen (bool), similarity (float), reason (str)
        """
        resized_a = resize_screenshot(screenshot_a, self.max_screenshot_size)
        resized_b = resize_screenshot(screenshot_b, self.max_screenshot_size)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SCREEN_COMPARISON_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_to_base64(resized_a)},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_to_base64(resized_b)},
                    },
                ],
            }
        ]

        try:
            response_text = await self._chat_completion(messages, max_tokens=256)
            result = self._parse_json_response(response_text)
            return {
                "is_same_screen": result.get("is_same_screen", False),
                "similarity": result.get("similarity", 0.0),
                "reason": result.get("reason", ""),
            }
        except Exception as e:
            logger.error(f"Screen comparison failed: {e}")
            # Default to "different" on error to avoid getting stuck
            return {"is_same_screen": False, "similarity": 0.0, "reason": f"Error: {e}"}

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse JSON response: {text[:200]}...")
            return {}

    @property
    def stats(self) -> dict:
        """Return usage statistics."""
        return {
            "requests": self._request_count,
            "total_tokens": self._total_tokens,
        }
