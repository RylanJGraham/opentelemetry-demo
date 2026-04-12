"""
Enhanced Vision LLM integration via OpenRouter.
Analyzes screenshots with batch processing, cost tracking, and intelligent caching.
"""

import json
import logging
from typing import Any, Optional

import httpx

from .utils import Config, image_to_base64, resize_screenshot, CostTracker

logger = logging.getLogger("explorer.vision")

# ── Prompts ──────────────────────────────────────────────────────────

SCREEN_ANALYSIS_PROMPT = """You are an expert mobile UI analyst. Analyze this screenshot of a mobile app screen.

You ALSO have the accessibility tree data below (if available) to help identify elements accurately.

**Accessibility Tree:**
{accessibility_tree}

**Instructions:**
1. Give this screen a short, descriptive name (e.g., "Login Screen", "Product List", "Settings")
2. Categorize the screen type (e.g., "authentication", "list", "detail", "settings", "navigation", "form", "modal", "error", "checkout", "profile")
3. Describe what you see in 1-2 sentences
4. Identify the main purpose of this screen (e.g., "browse products", "complete purchase", "user login")
5. List ALL interactive elements you can identify, ordered by their Y position (top to bottom)

For each interactive element, provide:
- A unique ID like "el_1", "el_2", etc.
- The element type: "button", "text_input", "link", "toggle", "checkbox", "tab", "menu_item", "card", "icon_button", "dropdown", "back_button", "nav_item", "submit", "cancel"
- A short label describing what it does
- Estimated center coordinates (x, y) based on the image dimensions
- Priority: "high" (primary actions, navigation), "medium" (secondary actions), "low" (minor/decorative)
- Any text content visible on the element
- Accessibility ID if apparent (e.g., testID, accessibilityLabel)

Also identify screen-level features:
- Does this screen have a form?
- Does this screen have a scrollable list?
- Does this screen have search functionality?
- Is this a modal/popup?

Respond with ONLY valid JSON in this exact format:
{{
  "screen_name": "Screen Name",
  "screen_type": "type",
  "description": "What this screen shows",
  "main_purpose": "Primary user goal on this screen",
  "interactive_elements": [
    {{
      "id": "el_1",
      "type": "button",
      "label": "Sign In",
      "x": 200,
      "y": 450,
      "priority": "high",
      "text_content": "Sign In",
      "accessibility_id": ""
    }}
  ],
  "features": {{
    "has_form": false,
    "has_list": false,
    "has_search": false,
    "is_modal": false
  }},
  "user_flows": ["login", "registration"]
}}"""

SCREEN_COMPARISON_PROMPT = """Compare these two mobile app screenshots and determine if they show the SAME screen or DIFFERENT screens.

Consider:
- Same layout but different content (e.g., scrolled) = SAME screen
- Same screen with a modal/popup overlay = DIFFERENT screen 
- Different layouts entirely = DIFFERENT screen
- Same screen with minor state changes (loading indicators, etc.) = SAME screen

Also estimate the visual similarity as a percentage.

Respond with ONLY valid JSON:
{{
  "is_same_screen": true/false,
  "similarity": 0.0 to 1.0,
  "reason": "Brief explanation"
}}"""

SCREEN_SUMMARY_PROMPT = """Given a collection of screens from a mobile app, provide a comprehensive summary.

Screens:
{screens_data}

Provide:
1. Total count of unique screen types
2. Most important screens (entry points, core functionality)
3. Apparent user flows (e.g., "Browse → Product → Cart → Checkout")
4. Missing screens that would be expected (e.g., if there's login but no signup)
5. Recommended test scenarios

Respond with ONLY valid JSON:
{{
  "summary": "Brief overview of the app structure",
  "screen_types": {{"type": count}},
  "key_screens": ["screen_id_1", "screen_id_2"],
  "user_flows": [
    {{"name": "Purchase Flow", "screens": ["...", "..."]}}
  ],
  "gaps": ["Missing signup screen"],
  "recommended_tests": [
    {{"name": "Complete Purchase", "priority": "high", "steps": [...]}}
  ]
}}"""

ELEMENT_REFINEMENT_PROMPT = """Given a screenshot and a list of detected UI elements, refine and enhance the element information.

Current elements:
{elements}

For each element:
1. Verify the element type is correct
2. Suggest a better, descriptive label if needed
3. Identify if this element is part of a repeated pattern (list item)
4. Suggest what test assertion could be made for this element

Respond with ONLY valid JSON - an array of enhanced elements:
[
  {{
    "id": "el_1",
    "refined_type": "button",
    "refined_label": "Add to Cart",
    "is_list_item": false,
    "suggested_assertion": "element is visible and enabled",
    "test_importance": "high"
  }}
]"""


class VisionAnalyzer:
    """Analyzes mobile screenshots using a vision LLM via OpenRouter with cost tracking."""

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
        self.cost_tracker = CostTracker(self.model)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def _chat_completion(
        self, messages: list[dict], max_tokens: int = None, track_cost: bool = True
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

            usage = data.get("usage", {})
            if track_cost:
                self.cost_tracker.add_request(
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                )

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
            dict with screen_name, screen_type, description, interactive_elements, features
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
            if "main_purpose" not in result:
                result["main_purpose"] = ""
            if "interactive_elements" not in result:
                result["interactive_elements"] = []
            if "features" not in result:
                result["features"] = {"has_form": False, "has_list": False, "has_search": False, "is_modal": False}
            if "user_flows" not in result:
                result["user_flows"] = []

            logger.info(
                f"[ai]🔍 Analyzed screen: {result['screen_name']}[/ai] "
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
                "main_purpose": "",
                "interactive_elements": [],
                "features": {"has_form": False, "has_list": False, "has_search": False, "is_modal": False},
                "user_flows": [],
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

    async def batch_analyze_screens(
        self, screens_data: list[dict]
    ) -> dict:
        """
        Analyze multiple screens together to find patterns and flows.
        More cost-effective than individual analysis.
        
        Args:
            screens_data: List of {screen_id, name, type, description} dicts
        
        Returns:
            Summary analysis with flows, gaps, and test recommendations
        """
        # Format screens data for prompt
        screens_text = json.dumps(screens_data, indent=2)
        prompt = SCREEN_SUMMARY_PROMPT.format(screens_data=screens_text)

        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ]

        try:
            response_text = await self._chat_completion(messages, max_tokens=2048)
            result = self._parse_json_response(response_text)
            return result
        except Exception as e:
            logger.error(f"Batch analysis failed: {e}")
            return {
                "summary": "Analysis failed",
                "screen_types": {},
                "key_screens": [],
                "user_flows": [],
                "gaps": [],
                "recommended_tests": [],
            }

    async def refine_elements(
        self, screenshot_bytes: bytes, elements: list[dict]
    ) -> list[dict]:
        """
        Refine element detection results for better test generation.
        
        Returns:
            List of enhanced element data with test suggestions
        """
        if not elements:
            return []

        resized = resize_screenshot(screenshot_bytes, self.max_screenshot_size)
        image_b64 = image_to_base64(resized)
        elements_text = json.dumps(elements, indent=2)
        prompt = ELEMENT_REFINEMENT_PROMPT.format(elements=elements_text)

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
            response_text = await self._chat_completion(messages, max_tokens=1024)
            result = self._parse_json_response(response_text)
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            logger.error(f"Element refinement failed: {e}")
            return []

    def _parse_json_response(self, text: str) -> Any:
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
            # Try array format
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse JSON response: {text[:200]}...")
            return {}

    @property
    def stats(self) -> dict:
        """Return usage statistics including cost."""
        return self.cost_tracker.get_stats()

    async def generate_story_from_screens(
        self, screens: list[dict], transitions: list[dict]
    ) -> dict:
        """
        Use the vision LLM to synthesize a Given/When/Then E2E test story
        from a list of screens and the transitions between them.
        
        Args:
            screens: List of screen dicts with {id, name, screen_type, description, elements}
            transitions: List of transition dicts with {from_screen_id, to_screen_id, action_type, element_id, action_detail}
        
        Returns:
            dict with story structure: {name, description, given, when, then, steps}
        """
        screens_text = json.dumps(
            [{"id": s["id"], "name": s.get("name"), "type": s.get("screen_type"), 
              "description": s.get("description"), "element_count": len(s.get("elements", []))} 
             for s in screens], indent=2
        )
        transitions_text = json.dumps(
            [{"from": t.get("from_screen_id"), "to": t.get("to_screen_id"), 
              "action": t.get("action_type"), "detail": t.get("action_detail")}
             for t in transitions], indent=2
        )
        
        prompt = f"""You are an expert QA engineer. Given the following screen flow from a mobile app,
generate a structured E2E test story in Given/When/Then format.

**Screens in this flow:**
{screens_text}

**Transitions between screens:**
{transitions_text}

Generate a test story that:
1. Has a clear, descriptive name
2. Describes the user's goal
3. Uses Given/When/Then structure for the scenario
4. Produces concrete, actionable test steps with assertions

Respond with ONLY valid JSON:
{{
  "name": "User can complete purchase",
  "description": "Verifies the full purchase flow from browsing to checkout",
  "scenario": {{
    "given": "The user is on the Home screen",
    "when": "The user navigates to a product and adds it to cart",
    "then": "The user should see the item in their cart"
  }},
  "steps": [
    {{
      "step_number": 1,
      "action_type": "navigate",
      "screen_id": "screen_id",
      "description": "User lands on the Home screen",
      "assertion": "Home screen is visible with product list",
      "assertion_type": "visible"
    }}
  ],
  "priority": "high",
  "tags": ["purchase", "checkout"]
}}"""

        messages = [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]

        try:
            response_text = await self._chat_completion(messages, max_tokens=1500)
            result = self._parse_json_response(response_text)
            return result
        except Exception as e:
            logger.error(f"Story generation failed: {e}")
            return {
                "name": "Auto-generated flow",
                "description": "Story generation failed, manual editing required",
                "scenario": {"given": "", "when": "", "then": ""},
                "steps": [],
                "priority": "medium",
                "tags": ["auto"],
            }
