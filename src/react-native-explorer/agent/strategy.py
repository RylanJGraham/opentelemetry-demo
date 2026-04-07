"""
Enhanced Exploration strategy / decision engine with clustering and path optimization.
Determines what action to take next based on current state, history, and screen clusters.
"""

import logging
import random
from typing import Optional, List, Dict

logger = logging.getLogger("explorer.strategy")

# Element type priority for exploration (higher = explore first)
ELEMENT_PRIORITY = {
    "button": 10,
    "submit": 10,
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
    "cancel": 2,
    "back_button": 1,
}

# Priority label weights
PRIORITY_WEIGHTS = {
    "high": 3,
    "medium": 2,
    "low": 1,
}

# Screen type priorities for exploration order
SCREEN_TYPE_PRIORITY = {
    "navigation": 10,
    "list": 9,
    "authentication": 8,
    "form": 7,
    "detail": 6,
    "settings": 5,
    "modal": 4,
    "error": 3,
    "unknown": 1,
}


class ExplorationStrategy:
    """
    Decides the next action during app exploration.
    Uses intelligent DFS with element priority scoring and screen clustering.
    """

    def __init__(self, config: dict):
        self.max_actions_per_screen = config.get("max_actions_per_screen", 15)
        self.stuck_threshold = config.get("stuck_threshold", 3)
        self.max_back_presses = config.get("max_back_presses", 3)
        self.explore_depth = config.get("explore_depth", "full")
        self.enable_clustering = config.get("enable_clustering", True)

        # State tracking
        self._screen_action_count: dict[str, int] = {}  # screen_id -> action count
        self._consecutive_same_screen: int = 0
        self._last_screen_id: Optional[str] = None
        self._back_press_count: int = 0
        self._visited_screens: set[str] = set()
        self._exploration_stack: list[str] = []  # DFS stack
        self._screen_clusters: dict[str, str] = {}  # screen_id -> cluster_id
        self._cluster_representatives: set[str] = set()  # screens that represent clusters
        
        # Smart navigation tracking
        self._dead_ends: set[str] = set()  # screens that lead nowhere new
        self._high_value_screens: set[str] = set()  # screens with many transitions
        self._pending_screens: list[str] = []  # screens to visit

    def decide_next_action(
        self,
        current_screen_id: str,
        unexplored_elements: list[dict],
        all_elements: list[dict],
        screen_fully_explored: bool = False,
        screen_type: str = "unknown",
        available_transitions: list[dict] = None,
    ) -> dict:
        """
        Decide the next exploration action.
        
        Args:
            current_screen_id: ID of current screen
            unexplored_elements: Elements not yet interacted with
            all_elements: All elements on screen
            screen_fully_explored: Whether screen is marked fully explored
            screen_type: Type of current screen (list, form, etc.)
            available_transitions: Known outgoing transitions from this screen
        
        Returns:
            dict with keys:
                - action: "tap", "swipe", "back", "type", "done", "skip"
                - element: the target element (if applicable)
                - reason: why this action was chosen
                - coordinates: (x, y) for tap actions
        """
        available_transitions = available_transitions or []
        
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

        # 3. Prioritize by screen type
        if count == 0 and screen_type in SCREEN_TYPE_PRIORITY:
            priority = SCREEN_TYPE_PRIORITY[screen_type]
            if priority >= 8:  # High-priority screen type
                logger.info(f"⭐ High-priority screen type: {screen_type}")

        # 4. No unexplored elements left
        if not unexplored_elements:
            if screen_fully_explored or self._should_mark_explored(current_screen_id, available_transitions):
                logger.info(f"✅ Screen '{current_screen_id}' fully explored")
                self._dead_ends.add(current_screen_id)
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

        # 5. Select best element to interact with
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

        # 6. Fallback — try backtrack
        return self._try_backtrack("No actionable elements found")

    def _score_elements(self, elements: list[dict]) -> list[dict]:
        """Score and sort elements by exploration priority."""
        scored = []
        for el in elements:
            el_type = el.get("type", "unknown")
            el_priority = el.get("priority", "medium")

            # Base score from element type and priority
            type_score = ELEMENT_PRIORITY.get(el_type, 3)
            priority_multiplier = PRIORITY_WEIGHTS.get(el_priority, 1)
            score = type_score * priority_multiplier

            # Slight randomness to avoid deterministic loops
            score += random.uniform(-0.5, 0.5)

            # Penalize elements too close to screen edges (likely system UI)
            x, y = el.get("x", 0), el.get("y", 0)
            if y < 100 or y > 2200:  # Status bar / nav bar area
                score *= 0.2
            if x < 30 or x > 1050:  # Screen edges
                score *= 0.5
            
            # Bonus for elements with good labels (indicates important functionality)
            label = el.get("label", "")
            if label and len(label) > 2:
                score += 1
            
            # Bonus for elements with text content
            if el.get("text_content"):
                score += 0.5

            scored.append({"element": el, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _element_to_action(self, element: dict) -> str:
        """Determine the action type based on element type."""
        el_type = element.get("type", "unknown")
        if el_type in ("text_input",):
            return "type"
        return "tap"

    def _should_mark_explored(self, screen_id: str, transitions: list[dict]) -> bool:
        """Determine if a screen should be marked as fully explored."""
        # If we've seen many transitions from this screen, it's valuable
        if len(transitions) >= 3:
            self._high_value_screens.add(screen_id)
        
        # If we've tried most interactive elements
        action_count = self._screen_action_count.get(screen_id, 0)
        if action_count >= self.max_actions_per_screen * 0.7:
            return True
        
        return False

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
            self._dead_ends.add(screen_id)
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

    def register_screen_cluster(self, screen_id: str, cluster_id: str, is_representative: bool = False):
        """Register that a screen belongs to a cluster."""
        self._screen_clusters[screen_id] = cluster_id
        if is_representative:
            self._cluster_representatives.add(screen_id)

    def suggest_next_screen_to_explore(self, unexplored_screens: list[str]) -> Optional[str]:
        """
        Suggest which unexplored screen to visit next based on strategy.
        Prioritizes screens from different clusters.
        """
        if not unexplored_screens:
            return None
        
        # Prioritize screens from clusters we haven't explored much
        cluster_counts: Dict[str, int] = {}
        for screen_id in self._visited_screens:
            cluster = self._screen_clusters.get(screen_id, "unknown")
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        
        # Score unexplored screens
        scored = []
        for screen_id in unexplored_screens:
            cluster = self._screen_clusters.get(screen_id, "unknown")
            # Prefer clusters with fewer visited screens
            cluster_visits = cluster_counts.get(cluster, 0)
            score = 100 - cluster_visits * 10
            scored.append((screen_id, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None

    def get_exploration_recommendations(self) -> list[dict]:
        """Get recommendations for continuing exploration."""
        recommendations = []
        
        # Find high-value screens to explore deeper
        for screen_id in self._high_value_screens:
            if screen_id not in self._dead_ends:
                recommendations.append({
                    "type": "explore_deeper",
                    "screen_id": screen_id,
                    "reason": "Screen has many transitions",
                })
        
        # Suggest checking dead ends again if we've found new patterns
        if len(self._visited_screens) > len(self._dead_ends) * 2:
            for screen_id in list(self._dead_ends)[:3]:
                recommendations.append({
                    "type": "revisit",
                    "screen_id": screen_id,
                    "reason": "Re-check screen with new context",
                })
        
        return recommendations

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
            "dead_ends": len(self._dead_ends),
            "high_value_screens": len(self._high_value_screens),
            "clusters_discovered": len(set(self._screen_clusters.values())),
        }
