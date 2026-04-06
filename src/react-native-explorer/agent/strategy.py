"""
Exploration strategy / decision engine.
Determines what action to take next based on the current screen state and history.
"""

import logging
import random
from typing import Optional

logger = logging.getLogger("explorer.strategy")

# Element type priority for exploration (higher = explore first)
ELEMENT_PRIORITY = {
    "button": 10,
    "card": 9,
    "link": 8,
    "nav_item": 8,
    "tab": 7,
    "menu_item": 7,
    "icon_button": 6,
    "dropdown": 5,
    "toggle": 4,
    "checkbox": 4,
    "text_input": 3,
    "back_button": 1,
}

# Priority label weights
PRIORITY_WEIGHTS = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


class ExplorationStrategy:
    """
    Decides the next action during app exploration.
    Uses a depth-first approach with element priority scoring.
    """

    def __init__(self, config: dict):
        self.max_actions_per_screen = config.get("max_actions_per_screen", 15)
        self.stuck_threshold = config.get("stuck_threshold", 3)
        self.max_back_presses = config.get("max_back_presses", 3)
        self.explore_depth = config.get("explore_depth", "full")

        # State tracking
        self._screen_action_count: dict[str, int] = {}  # screen_id -> action count
        self._consecutive_same_screen: int = 0
        self._last_screen_id: Optional[str] = None
        self._back_press_count: int = 0
        self._visited_screens: set[str] = set()
        self._exploration_stack: list[str] = []  # DFS stack

    def decide_next_action(
        self,
        current_screen_id: str,
        unexplored_elements: list[dict],
        all_elements: list[dict],
        screen_fully_explored: bool = False,
    ) -> dict:
        """
        Decide the next exploration action.
        
        Returns:
            dict with keys:
                - action: "tap", "swipe", "back", "type", "done", "skip"
                - element: the target element (if applicable)
                - reason: why this action was chosen
                - coordinates: (x, y) for tap actions
        """
        # Track visit
        self._visited_screens.add(current_screen_id)

        # Track consecutive same-screen visits
        if current_screen_id == self._last_screen_id:
            self._consecutive_same_screen += 1
        else:
            self._consecutive_same_screen = 0
            self._back_press_count = 0
            # Push to DFS stack if new screen
            if current_screen_id not in self._exploration_stack:
                self._exploration_stack.append(current_screen_id)

        self._last_screen_id = current_screen_id

        # Track per-screen action count
        count = self._screen_action_count.get(current_screen_id, 0)
        self._screen_action_count[current_screen_id] = count + 1

        # ── Decision logic ────────────────────────────────────────

        # 1. Stuck detection — same screen too many times
        if self._consecutive_same_screen >= self.stuck_threshold:
            return self._handle_stuck(current_screen_id)

        # 2. Max actions for this screen reached
        if count >= self.max_actions_per_screen:
            logger.info(f"📊 Max actions reached for screen '{current_screen_id}'")
            return self._try_backtrack("Max actions per screen reached")

        # 3. No unexplored elements left
        if not unexplored_elements:
            if screen_fully_explored:
                logger.info(f"✅ Screen '{current_screen_id}' fully explored")
                return self._try_backtrack("All elements explored")
            else:
                # Try scrolling to reveal more elements
                return {
                    "action": "swipe",
                    "element": None,
                    "reason": "No unexplored elements visible, scrolling to find more",
                    "coordinates": None,
                    "swipe": {"x1": 540, "y1": 1500, "x2": 540, "y2": 500},
                }

        # 4. Select best element to interact with
        scored = self._score_elements(unexplored_elements)
        if scored:
            best = scored[0]
            element = best["element"]
            action_type = self._element_to_action(element)
            return {
                "action": action_type,
                "element": element,
                "reason": f"Exploring {element.get('type', 'unknown')}: {element.get('label', 'unnamed')} (score: {best['score']:.1f})",
                "coordinates": (element.get("x", 0), element.get("y", 0)),
            }

        # 5. Fallback — try backtrack
        return self._try_backtrack("No actionable elements found")

    def _score_elements(self, elements: list[dict]) -> list[dict]:
        """Score and sort elements by exploration priority."""
        scored = []
        for el in elements:
            el_type = el.get("type", "unknown")
            el_priority = el.get("priority", "medium")

            score = ELEMENT_PRIORITY.get(el_type, 3) * PRIORITY_WEIGHTS.get(el_priority, 1)

            # Slight randomness to avoid deterministic loops
            score += random.uniform(-0.5, 0.5)

            # Penalize elements too close to screen edges (likely system UI)
            x, y = el.get("x", 0), el.get("y", 0)
            if y < 50 or y > 2300:  # Status bar / nav bar area
                score *= 0.3
            if x < 20 or x > 1060:  # Screen edges
                score *= 0.5

            scored.append({"element": el, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _element_to_action(self, element: dict) -> str:
        """Determine the action type based on element type."""
        el_type = element.get("type", "unknown")
        if el_type in ("text_input",):
            return "type"
        return "tap"

    def _handle_stuck(self, screen_id: str) -> dict:
        """Handle being stuck on the same screen."""
        self._consecutive_same_screen = 0

        if self._back_press_count < self.max_back_presses:
            self._back_press_count += 1
            return {
                "action": "back",
                "element": None,
                "reason": f"Stuck on screen (back press {self._back_press_count}/{self.max_back_presses})",
                "coordinates": None,
            }
        else:
            return {
                "action": "done",
                "element": None,
                "reason": "Stuck after max back presses, stopping this branch",
                "coordinates": None,
            }

    def _try_backtrack(self, reason: str) -> dict:
        """Try to go back to a previous screen."""
        if self._back_press_count < self.max_back_presses:
            self._back_press_count += 1
            return {
                "action": "back",
                "element": None,
                "reason": f"Backtracking: {reason}",
                "coordinates": None,
            }
        else:
            return {
                "action": "done",
                "element": None,
                "reason": f"Exploration branch complete: {reason}",
                "coordinates": None,
            }

    def reset_back_count(self):
        """Reset back press counter (call when a new screen is reached)."""
        self._back_press_count = 0

    @property
    def stats(self) -> dict:
        """Return exploration statistics."""
        return {
            "visited_screens": len(self._visited_screens),
            "total_actions": sum(self._screen_action_count.values()),
            "screen_action_counts": dict(self._screen_action_count),
        }
