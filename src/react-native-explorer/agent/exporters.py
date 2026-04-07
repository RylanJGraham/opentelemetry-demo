"""
E2E Test Exporters for various testing frameworks.
Supports Detox, Maestro, and Appium.
"""

import json
from typing import Any


def export_story(story: dict, format_name: str) -> str:
    """Export a single story to the specified format."""
    exporters = {
        "detox": _export_story_detox,
        "maestro": _export_story_maestro,
        "appium": _export_story_appium,
        "cypress": _export_story_cypress,
        "playwright": _export_story_playwright,
    }
    
    if format_name not in exporters:
        raise ValueError(f"Unknown format: {format_name}. Available: {list(exporters.keys())}")
    
    return exporters[format_name](story)


def export_to_detox(stories: list[dict]) -> str:
    """Export all stories as a Detox test suite."""
    lines = [
        "// Auto-generated Detox E2E tests",
        "import { device, element, by, expect } from 'detox';",
        "",
        "describe('Exploration-based E2E Tests', () => {",
        "  beforeAll(async () => {",
        "    await device.launchApp();",
        "  });",
        "",
        "  beforeEach(async () => {",
        "    await device.reloadReactNative();",
        "  });",
        "",
    ]
    
    for story in stories:
        test_name = story.get("name", "Untitled").replace("'", "\\'")
        lines.append(f"  it('{test_name}', async () => {{")
        
        for step in story.get("steps", []):
            detox_line = _convert_step_to_detox(step)
            if detox_line:
                lines.append(f"    {detox_line}")
        
        lines.append("  });")
        lines.append("")
    
    lines.append("});")
    return "\n".join(lines)


def _export_story_detox(story: dict) -> str:
    """Export a single story as Detox test."""
    lines = [
        "import { device, element, by, expect } from 'detox';",
        "",
        f"it('{story.get('name', 'Test').replace(chr(39), chr(92)+chr(39))}', async () => {{",
    ]
    
    for step in story.get("steps", []):
        detox_line = _convert_step_to_detox(step)
        if detox_line:
            lines.append(f"  {detox_line}")
    
    lines.append("});")
    return "\n".join(lines)


def _convert_step_to_detox(step: dict) -> str:
    """Convert a story step to Detox code."""
    action = step.get("action_type", "tap")
    element_id = step.get("element_id", "")
    screen_id = step.get("screen_id", "")
    coords = step.get("coordinates")
    assertion = step.get("assertion", "")
    data = step.get("data", {})
    
    if action == "start":
        return "// Starting test"
    
    if action == "tap":
        if element_id:
            return f"await element(by.id('{element_id}')).tap();"
        elif coords:
            x, y = coords
            return f"await device.tap({{ x: {x}, y: {y} }});"
    
    if action == "type":
        text = data.get("text", "test input") if isinstance(data, dict) else "test input"
        if element_id:
            return f"await element(by.id('{element_id}')).typeText('{text}');"
    
    if action == "navigate":
        return f"// Navigated to {screen_id}"
    
    if action == "assert":
        if assertion == "visible":
            if element_id:
                return f"await expect(element(by.id('{element_id}'))).toBeVisible();"
    
    if action == "swipe":
        direction = data.get("direction", "up") if isinstance(data, dict) else "up"
        return f"await element(by.id('scrollView')).swipe('{direction}');"
    
    if action == "back":
        return "await device.pressBack();"
    
    return f"// Unknown action: {action}"


def export_to_maestro(stories: list[dict]) -> dict:
    """Export all stories as Maestro flows."""
    flows = {}
    
    for story in stories:
        flow_name = story.get("name", "flow").lower().replace(" ", "_").replace("-", "_")
        flows[flow_name] = _export_story_maestro(story)
    
    return flows


def _export_story_maestro(story: dict) -> str:
    """Export a single story as Maestro YAML flow."""
    lines = [
        "# Auto-generated Maestro flow",
        f"# Story: {story.get('name', 'Untitled')}",
        f"# Description: {story.get('description', '')}",
        "",
        "appId: ${APP_ID}",
        "---",
    ]
    
    for step in story.get("steps", []):
        maestro_line = _convert_step_to_maestro(step)
        if maestro_line:
            if isinstance(maestro_line, list):
                lines.extend(maestro_line)
            else:
                lines.append(maestro_line)
    
    return "\n".join(lines)


def _convert_step_to_maestro(step: dict) -> str | list[str]:
    """Convert a story step to Maestro YAML."""
    action = step.get("action_type", "tap")
    element_id = step.get("element_id", "")
    screen_id = step.get("screen_id", "")
    coords = step.get("coordinates")
    data = step.get("data", {})
    assertion = step.get("assertion", "")
    
    if action == "start":
        return f"# Starting: {data.get('screen_name', '') if isinstance(data, dict) else ''}"
    
    if action == "tap":
        if element_id:
            return f"- tapOn:\n    id: \"{element_id}\""
        elif coords:
            x, y = coords
            return f"- tapOn:\n    point: {x}, {y}"
    
    if action == "type":
        text = data.get("text", "test input") if isinstance(data, dict) else "test input"
        return f'- inputText: "{text}"'
    
    if action == "navigate":
        return f"# Navigate to {screen_id}"
    
    if action == "assert":
        if assertion == "visible":
            if element_id:
                return f"- assertVisible:\n    id: \"{element_id}\""
    
    if action == "swipe":
        direction = data.get("direction", "up") if isinstance(data, dict) else "up"
        return f"- swipe:\n    direction: {direction}"
    
    if action == "back":
        return "- pressBack"
    
    if action == "wait":
        return "- waitForAnimationToEnd"
    
    return f"# Unknown action: {action}"


def export_to_appium(stories: list[dict]) -> str:
    """Export all stories as Appium Python tests."""
    lines = [
        "# Auto-generated Appium tests",
        "import unittest",
        "from appium import webdriver",
        "from appium.options.android import UiAutomator2Options",
        "from selenium.webdriver.common.by import By",
        "from selenium.webdriver.support.ui import WebDriverWait",
        "from selenium.webdriver.support import expected_conditions as EC",
        "",
        "class ExplorationTests(unittest.TestCase):",
        "    def setUp(self):",
        "        options = UiAutomator2Options()",
        "        options.platform_name = 'Android'",
        "        options.device_name = ' emulator'",
        "        self.driver = webdriver.Remote('http://localhost:4723', options=options)",
        "",
        "    def tearDown(self):",
        "        self.driver.quit()",
        "",
    ]
    
    for story in stories:
        method_name = story.get("name", "test_flow").lower().replace(" ", "_").replace("-", "_")
        if not method_name.startswith("test_"):
            method_name = f"test_{method_name}"
        
        lines.append(f"    def {method_name}(self):")
        
        for step in story.get("steps", []):
            appium_line = _convert_step_to_appium(step)
            if appium_line:
                lines.append(f"        {appium_line}")
        
        lines.append("")
    
    lines.append("if __name__ == '__main__':")
    lines.append("    unittest.main()")
    
    return "\n".join(lines)


def _export_story_appium(story: dict) -> str:
    """Export a single story as Appium test."""
    return export_to_appium([story])


def _convert_step_to_appium(step: dict) -> str:
    """Convert a story step to Appium Python code."""
    action = step.get("action_type", "tap")
    element_id = step.get("element_id", "")
    coords = step.get("coordinates")
    data = step.get("data", {})
    assertion = step.get("assertion", "")
    
    if action == "start":
        return "# Starting test"
    
    if action == "tap":
        if element_id:
            return f"self.driver.find_element(By.ID, '{element_id}').click()"
        elif coords:
            x, y = coords
            return f"self.driver.tap([({x}, {y})])"
    
    if action == "type":
        text = data.get("text", "test input") if isinstance(data, dict) else "test input"
        if element_id:
            return f"self.driver.find_element(By.ID, '{element_id}').send_keys('{text}')"
    
    if action == "navigate":
        return f"# Navigate"
    
    if action == "assert":
        if assertion == "visible":
            if element_id:
                return f"WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, '{element_id}')))"
    
    if action == "swipe":
        return "# Swipe gesture"
    
    if action == "back":
        return "self.driver.press_keycode(4)  # Android back button"
    
    return f"# Unknown action: {action}"


def _export_story_cypress(story: dict) -> str:
    """Export a single story as Cypress test."""
    lines = [
        "// Auto-generated Cypress test",
        f"describe('{story.get('name', 'Test').replace(chr(39), chr(92)+chr(39))}', () => {{",
        "  it('should complete the flow', () => {",
    ]
    
    for step in story.get("steps", []):
        cypress_line = _convert_step_to_cypress(step)
        if cypress_line:
            lines.append(f"    {cypress_line}")
    
    lines.append("  });")
    lines.append("});")
    return "\n".join(lines)


def _convert_step_to_cypress(step: dict) -> str:
    """Convert a story step to Cypress code."""
    action = step.get("action_type", "tap")
    element_id = step.get("element_id", "")
    data = step.get("data", {})
    
    if action == "start":
        return "cy.visit('/');"
    
    if action == "tap":
        if element_id:
            return f"cy.get('[data-testid={element_id}]').click();"
        return "cy.get('button').first().click();"
    
    if action == "type":
        text = data.get("text", "test") if isinstance(data, dict) else "test"
        if element_id:
            return f"cy.get('[data-testid={element_id}]').type('{text}');"
    
    if action == "assert":
        if element_id:
            return f"cy.get('[data-testid={element_id}]').should('be.visible');"
    
    return f"// {action}"


def _export_story_playwright(story: dict) -> str:
    """Export a single story as Playwright test."""
    lines = [
        "// Auto-generated Playwright test",
        "import { test, expect } from '@playwright/test';",
        "",
        f"test('{story.get('name', 'Test').replace(chr(39), chr(92)+chr(39))}', async ({{ page }}) => {{",
    ]
    
    for step in story.get("steps", []):
        pw_line = _convert_step_to_playwright(step)
        if pw_line:
            lines.append(f"  {pw_line}")
    
    lines.append("});")
    return "\n".join(lines)


def _convert_step_to_playwright(step: dict) -> str:
    """Convert a story step to Playwright code."""
    action = step.get("action_type", "tap")
    element_id = step.get("element_id", "")
    data = step.get("data", {})
    
    if action == "start":
        return "await page.goto('/');"
    
    if action == "tap":
        if element_id:
            return f"await page.locator('[data-testid={element_id}]').click();"
        return "await page.locator('button').first().click();"
    
    if action == "type":
        text = data.get("text", "test") if isinstance(data, dict) else "test"
        if element_id:
            return f"await page.locator('[data-testid={element_id}]').fill('{text}');"
    
    if action == "assert":
        if element_id:
            return f"await expect(page.locator('[data-testid={element_id}]')).toBeVisible();"
    
    return f"// {action}"


def generate_test_recommendations(graph_data: dict) -> list[dict]:
    """
    Analyze the screen graph and generate recommended test scenarios.
    
    Returns list of recommended stories to create.
    """
    recommendations = []
    
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    
    # Find authentication screens
    auth_screens = [n for n in nodes if n.get("screen_type") == "authentication"]
    if auth_screens:
        recommendations.append({
            "name": "Login Flow",
            "description": "Test user authentication",
            "priority": "high",
            "screens": [s["id"] for s in auth_screens[:2]],
        })
    
    # Find checkout/purchase flows
    checkout_screens = [n for n in nodes if n.get("screen_type") in ["checkout", "cart"]]
    if checkout_screens:
        recommendations.append({
            "name": "Purchase Flow",
            "description": "Complete a purchase transaction",
            "priority": "high",
            "screens": [s["id"] for s in checkout_screens[:3]],
        })
    
    # Find form screens
    form_screens = [n for n in nodes if n.get("screen_type") == "form"]
    for screen in form_screens[:2]:
        recommendations.append({
            "name": f"Form Submission - {screen.get('name', 'Unknown')}",
            "description": f"Test form on {screen.get('name')}",
            "priority": "medium",
            "screens": [screen["id"]],
        })
    
    # Find search functionality
    search_screens = [n for n in nodes if n.get("features", {}).get("has_search")]
    if search_screens:
        recommendations.append({
            "name": "Search Functionality",
            "description": "Test search feature",
            "priority": "medium",
            "screens": [s["id"] for s in search_screens[:2]],
        })
    
    # Critical path test (longest path through app)
    if edges:
        # Simple critical path: most connected screen
        connection_counts = {}
        for edge in edges:
            connection_counts[edge["source"]] = connection_counts.get(edge["source"], 0) + 1
            connection_counts[edge["target"]] = connection_counts.get(edge["target"], 0) + 1
        
        if connection_counts:
            most_connected = max(connection_counts, key=connection_counts.get)
            screen = next((n for n in nodes if n["id"] == most_connected), None)
            if screen:
                recommendations.append({
                    "name": "Critical Path - Main Navigation",
                    "description": f"Test main navigation through {screen.get('name')}",
                    "priority": "high",
                    "screens": [most_connected],
                })
    
    return recommendations
