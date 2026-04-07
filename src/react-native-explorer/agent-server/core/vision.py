"""AI vision analysis for screen understanding."""
import base64
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from functools import lru_cache

from openai import AsyncOpenAI
from core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from core.utils import ImageHasher

logger = logging.getLogger("agent.vision")


@dataclass
class ScreenAnalysis:
    """Result of AI screen analysis."""
    name: str
    screen_type: str
    description: str
    key_elements: List[str]
    purpose: str  # What this screen is for


class VisionAnalyzer:
    """Uses AI vision to analyze and understand screens."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key or OPENROUTER_API_KEY,
        )
        self.model = model or "openai/gpt-4o-mini"
        
        # In-memory cache for screen analysis
        self._analysis_cache: Dict[str, ScreenAnalysis] = {}
        
        # Stats
        self._requests = 0
        self._errors = 0
        self._cache_hits = 0
    
    def get_stats(self) -> Dict:
        return {
            "requests": self._requests,
            "errors": self._errors,
            "cache_hits": self._cache_hits
        }
    
    async def analyze_screen(self, screenshot_bytes: bytes, structure_hash: str,
                            elements: List[Dict]) -> ScreenAnalysis:
        """Analyze a screen to understand what it is."""
        
        # Check cache first
        if structure_hash in self._analysis_cache:
            self._cache_hits += 1
            return self._analysis_cache[structure_hash]
        
        # Prepare element summary for AI (top 10 most important)
        element_summary = []
        for i, el in enumerate(elements[:10]):
            el_type = el.get('type', 'unknown')
            label = el.get('label', '') or el.get('text', '')[:50]
            if label or el_type in ['button', 'imagebutton']:
                element_summary.append(f"{i+1}. {el_type}: {label or 'unnamed'}")
        
        element_text = "\n".join(element_summary) if element_summary else "No labeled elements found"
        
        # Encode screenshot
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
        
        prompt = f"""Analyze this mobile app screen and provide structured information.

SCREEN ELEMENTS:
{element_text}

Respond with ONLY this JSON format:
{{
    "name": "Short descriptive name (e.g., 'Product List', 'Cart Screen')",
    "screen_type": "home|list|detail|cart|checkout|profile|menu|modal|other",
    "description": "Brief description of what the screen shows",
    "key_elements": ["List of 2-4 important interactive elements"],
    "purpose": "What the user does on this screen (e.g., 'Browse products')"
}}"""

        try:
            self._requests += 1
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_b64}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            result = ScreenAnalysis(
                name=data.get('name', 'Unknown Screen'),
                screen_type=data.get('screen_type', 'unknown'),
                description=data.get('description', ''),
                key_elements=data.get('key_elements', []),
                purpose=data.get('purpose', '')
            )
            
            # Cache the result
            self._analysis_cache[structure_hash] = result
            return result
            
        except Exception as e:
            self._errors += 1
            logger.error(f"AI analysis failed: {e}")
            result = ScreenAnalysis(
                name="Unknown Screen",
                screen_type="unknown",
                description="",
                key_elements=[],
                purpose=""
            )
            self._analysis_cache[structure_hash] = result
            return result
    
    async def suggest_elements_to_tap(self, screenshot_bytes: bytes, 
                                      elements: List[Dict],
                                      already_tapped: List[int]) -> List[int]:
        """Ask AI which elements are most valuable to tap."""
        
        if not elements:
            return []
        
        # Filter to interactive elements
        candidates = []
        for i, el in enumerate(elements):
            if i in already_tapped:
                continue
            
            x = el.get('x', 0)
            y = el.get('y', 0)
            w = el.get('width', 0)
            h = el.get('height', 0)
            
            # Skip tiny or off-screen elements
            if w < 30 or h < 30 or x < 0 or y < 100 or y > 2000:
                continue
            
            el_type = el.get('type', 'unknown')
            label = el.get('label', '') or el.get('text', '')[:50]
            
            candidates.append({
                "idx": i,
                "type": el_type,
                "label": label or "unnamed",
                "rect": f"({x},{y},{w},{h})"
            })
        
        if len(candidates) <= 3:
            # Not many options, just return all
            return [c["idx"] for c in candidates]
        
        # Ask AI to prioritize
        candidates_json = json.dumps(candidates[:15])  # Limit to top 15
        
        prompt = f"""Given these UI elements on a mobile app screen, rank them by importance for exploration.

ALREADY TAPPED: {already_tapped}

CANDIDATE ELEMENTS:
{candidates_json}

Respond with ONLY a JSON array of indices to tap, in order of priority:
[3, 0, 5, 1]

Focus on:
1. Navigation items (tabs, menus)
2. Content items (product cards, list items)
3. Action buttons (add to cart, buy now)
4. Skip decorative elements and ads"""

        try:
            self._requests += 1
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            # Handle both direct array and {"indices": [...]} format
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "indices" in data:
                return data["indices"]
            else:
                return [c["idx"] for c in candidates[:5]]
                
        except Exception as e:
            self._errors += 1
            logger.warning(f"AI element suggestion failed: {e}")
            # Fallback: return first few untapped
            return [c["idx"] for c in candidates[:5]]
