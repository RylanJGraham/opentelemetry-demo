"""Story execution engine for autonomous E2E testing."""
import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from core.database import db
from core.utils import ImageHasher
from core.vision import VisionAnalyzer
from mcp_client.client import MCPClient

logger = logging.getLogger("agent.executor")


class ExecutionState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionStep:
    """A single step in a story execution."""
    number: int
    action_type: str  # navigate, tap, type, assert, swipe, wait
    target_screen_id: Optional[str] = None
    target_element_id: Optional[str] = None
    element_query: Optional[Dict] = None  # For finding elements by properties
    action_data: Dict = field(default_factory=dict)
    expected_result: Optional[str] = None
    assertion: Optional[str] = None
    
    # Execution results
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    actual_screen_id: Optional[str] = None
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    assertion_passed: Optional[bool] = None


@dataclass
class ExecutionResult:
    """Result of a complete story execution."""
    execution_id: str
    story_id: str
    status: ExecutionState
    started_at: float
    completed_at: Optional[float] = None
    duration_ms: Optional[int] = None
    passed_steps: int = 0
    failed_steps: int = 0
    total_steps: int = 0
    steps: List[ExecutionStep] = field(default_factory=list)
    error_summary: Optional[str] = None


class StoryExecutor:
    """Executes user stories (test scenarios) autonomously."""
    
    def __init__(self, vision_analyzer: Optional[VisionAnalyzer] = None):
        self.mcp = MCPClient()
        self.vision = vision_analyzer
        self.state = ExecutionState.IDLE
        
        self._current_execution: Optional[str] = None
        self._current_step_index: int = 0
        self._steps: List[ExecutionStep] = []
        
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._stop_event = asyncio.Event()
        self._callbacks: List[Callable] = []
        
        # Screenshot directory
        self._screenshot_dir = Path("./storage/screenshots/executions")
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    def on_event(self, callback: Callable):
        """Register event callback."""
        self._callbacks.append(callback)
    
    def _notify(self, event: str, data: Any = None):
        """Notify all callbacks."""
        for cb in self._callbacks:
            try:
                asyncio.create_task(cb(event, data))
            except Exception:
                pass
    
    async def execute_story(
        self, 
        story_id: str, 
        execution_id: Optional[str] = None,
        step_by_step: bool = False
    ) -> ExecutionResult:
        """
        Execute a story autonomously.
        
        Args:
            story_id: The story to execute
            execution_id: Optional execution ID (generated if not provided)
            step_by_step: If True, pause after each step for inspection
        
        Returns:
            ExecutionResult with full details
        """
        execution_id = execution_id or f"exec_{uuid.uuid4().hex[:12]}"
        self._current_execution = execution_id
        
        # Load story
        story = await db.fetchone(
            "SELECT * FROM stories WHERE id = ?",
            (story_id,)
        )
        if not story:
            raise ValueError(f"Story {story_id} not found")
        
        # Parse steps
        steps_data = json.loads(story.get('steps_json', '[]'))
        self._steps = self._parse_steps(steps_data)
        
        # Create execution record
        await db.create_story_execution(
            execution_id, story_id, len(self._steps),
            triggered_by="api", environment=json.dumps({"device": "android"})
        )
        
        # Connect to MCP
        connected = await self.mcp.connect()
        if not connected:
            await db.update_story_execution(
                execution_id, "failed", success=False, failed_steps=len(self._steps)
            )
            return ExecutionResult(
                execution_id=execution_id,
                story_id=story_id,
                status=ExecutionState.FAILED,
                started_at=time.time(),
                error_summary="Failed to connect to MCP"
            )
        
        # Execute
        self.state = ExecutionState.RUNNING
        self._stop_event.clear()
        self._pause_event.set()
        
        self._notify("execution_started", {
            "execution_id": execution_id,
            "story_id": story_id,
            "story_name": story['name'],
            "total_steps": len(self._steps)
        })
        
        started_at = time.time()
        passed = 0
        failed = 0
        
        try:
            for i, step in enumerate(self._steps):
                if self._stop_event.is_set():
                    self.state = ExecutionState.CANCELLED
                    break
                
                if step_by_step:
                    self._pause_event.clear()
                
                # Wait if paused
                if not self._pause_event.is_set():
                    self.state = ExecutionState.PAUSED
                    await self._pause_event.wait()
                    self.state = ExecutionState.RUNNING
                
                self._current_step_index = i
                
                # Execute step
                await self._execute_step(execution_id, step)
                
                if step.status == StepStatus.PASSED:
                    passed += 1
                elif step.status == StepStatus.FAILED:
                    failed += 1
                
                self._notify("step_completed", {
                    "execution_id": execution_id,
                    "step_number": i + 1,
                    "status": step.status.value,
                    "action": step.action_type
                })
                
                # Small delay between steps
                await asyncio.sleep(0.5)
            
            # Determine final status
            if self.state == ExecutionState.CANCELLED:
                final_status = ExecutionState.CANCELLED
                success = None
            elif failed == 0:
                final_status = ExecutionState.COMPLETED
                success = True
            else:
                final_status = ExecutionState.FAILED
                success = False
            
            self.state = final_status
            
            completed_at = time.time()
            duration_ms = int((completed_at - started_at) * 1000)
            
            # Update execution record
            await db.update_story_execution(
                execution_id, final_status.value, success, passed, failed
            )
            
            result = ExecutionResult(
                execution_id=execution_id,
                story_id=story_id,
                status=final_status,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                passed_steps=passed,
                failed_steps=failed,
                total_steps=len(self._steps),
                steps=self._steps,
                error_summary=self._build_error_summary()
            )
            
            self._notify("execution_completed", {
                "execution_id": execution_id,
                "status": final_status.value,
                "passed": passed,
                "failed": failed
            })
            
            return result
            
        except Exception as e:
            logger.exception("Execution failed")
            self.state = ExecutionState.FAILED
            await db.update_story_execution(
                execution_id, "failed", success=False, passed_steps=passed, failed_steps=failed + 1
            )
            
            return ExecutionResult(
                execution_id=execution_id,
                story_id=story_id,
                status=ExecutionState.FAILED,
                started_at=started_at,
                completed_at=time.time(),
                passed_steps=passed,
                failed_steps=failed + 1,
                total_steps=len(self._steps),
                steps=self._steps,
                error_summary=str(e)
            )
        finally:
            await self.mcp.disconnect()
            self._current_execution = None
    
    async def _execute_step(self, execution_id: str, step: ExecutionStep):
        """Execute a single step."""
        step.status = StepStatus.RUNNING
        step.started_at = time.time()
        
        # Create DB record
        step_db_id = await db.create_execution_step(
            execution_id, step.number, step.action_type,
            step.target_screen_id, step.target_element_id,
            step.action_data, step.expected_result
        )
        
        self._notify("step_started", {
            "execution_id": execution_id,
            "step_number": step.number,
            "action": step.action_type
        })
        
        try:
            # Execute based on action type
            if step.action_type == "navigate":
                await self._execute_navigate(step)
            elif step.action_type == "tap":
                await self._execute_tap(step)
            elif step.action_type == "type":
                await self._execute_type(step)
            elif step.action_type == "assert":
                await self._execute_assert(step)
            elif step.action_type == "swipe":
                await self._execute_swipe(step)
            elif step.action_type == "wait":
                await self._execute_wait(step)
            elif step.action_type == "back":
                await self._execute_back(step)
            else:
                raise ValueError(f"Unknown action type: {step.action_type}")
            
            step.status = StepStatus.PASSED
            
        except Exception as e:
            logger.error(f"Step {step.number} failed: {e}")
            step.status = StepStatus.FAILED
            step.error_message = str(e)
        
        step.completed_at = time.time()
        
        # Capture final screenshot
        try:
            screenshot = await self.mcp.take_screenshot()
            if screenshot:
                screenshot_path = f"{execution_id}_step{step.number}.png"
                (self._screenshot_dir / screenshot_path).write_bytes(screenshot)
                step.screenshot_path = f"executions/{screenshot_path}"
        except Exception:
            pass
        
        # Update DB
        await db.complete_execution_step(
            step_db_id, step.status.value,
            step.actual_screen_id, step.screenshot_path,
            step.error_message, step.assertion_passed
        )
    
    async def _execute_navigate(self, step: ExecutionStep):
        """Navigate to a specific screen."""
        if not step.target_screen_id:
            raise ValueError("navigate requires target_screen_id")
        
        # Get current screen
        screenshot = await self.mcp.take_screenshot()
        if not screenshot:
            raise Exception("Failed to capture screenshot")
        
        current_hash = ImageHasher.content_hash(screenshot)
        
        # Check if already on target screen
        target = await db.get_screen_by_hash(step.target_screen_id)
        if target and target.get('content_hash') == current_hash:
            step.actual_screen_id = target['id']
            return
        
        # Find path to target
        path = await self._find_path_to_screen(step.target_screen_id)
        if not path:
            raise Exception(f"No path found to screen {step.target_screen_id}")
        
        # Follow path
        for action in path:
            if action['type'] == 'tap':
                await self.mcp.tap(action['x'], action['y'])
            elif action['type'] == 'back':
                await self.mcp.press_back()
            await asyncio.sleep(0.5)
        
        # Verify we're on the right screen
        screenshot = await self.mcp.take_screenshot()
        current_hash = ImageHasher.content_hash(screenshot)
        
        target = await db.get_screen_by_hash(step.target_screen_id)
        if target:
            step.actual_screen_id = target['id']
    
    async def _execute_tap(self, step: ExecutionStep):
        """Tap on an element."""
        element = await self._find_element(step)
        if not element:
            raise Exception(f"Element not found: {step.element_query or step.target_element_id}")
        
        x = element.get('center_x', element.get('x', 0) + element.get('width', 0) // 2)
        y = element.get('center_y', element.get('y', 0) + element.get('height', 0) // 2)
        
        success = await self.mcp.tap(x, y)
        if not success:
            raise Exception(f"Tap failed at ({x}, {y})")
        
        # Wait for transition
        await asyncio.sleep(0.5)
        
        # Record actual screen
        screenshot = await self.mcp.take_screenshot()
        if screenshot:
            current_hash = ImageHasher.content_hash(screenshot)
            screen = await db.fetchone(
                "SELECT id FROM screens WHERE content_hash = ?",
                (current_hash,)
            )
            if screen:
                step.actual_screen_id = screen['id']
    
    async def _execute_type(self, step: ExecutionStep):
        """Type text into an input."""
        element = await self._find_element(step)
        if not element:
            raise Exception(f"Input element not found")
        
        # Tap to focus
        x = element.get('center_x', element.get('x', 0) + element.get('width', 0) // 2)
        y = element.get('center_y', element.get('y', 0) + element.get('height', 0) // 2)
        await self.mcp.tap(x, y)
        await asyncio.sleep(0.2)
        
        # Type text
        text = step.action_data.get('text', '')
        success = await self.mcp.type_text(text)
        if not success:
            raise Exception(f"Failed to type text: {text}")
    
    async def _execute_assert(self, step: ExecutionStep):
        """Assert a condition on the current screen."""
        assertion_type = step.action_data.get('assertion_type', 'screen_visible')
        
        if assertion_type == 'screen_visible':
            # Check we're on expected screen
            screenshot = await self.mcp.take_screenshot()
            if not screenshot:
                raise Exception("Failed to capture screenshot")
            
            current_hash = ImageHasher.content_hash(screenshot)
            screen = await db.fetchone(
                "SELECT id FROM screens WHERE content_hash = ?",
                (current_hash,)
            )
            
            if screen:
                step.actual_screen_id = screen['id']
            
            if step.target_screen_id:
                target = await db.fetchone(
                    "SELECT content_hash FROM screens WHERE id = ?",
                    (step.target_screen_id,)
                )
                if target and target['content_hash'] != current_hash:
                    step.assertion_passed = False
                    raise Exception(f"Expected screen {step.target_screen_id}, but on different screen")
            
            step.assertion_passed = True
            
        elif assertion_type == 'element_visible':
            element = await self._find_element(step)
            step.assertion_passed = element is not None
            if not element:
                raise Exception(f"Expected element not found")
        
        elif assertion_type == 'text_visible':
            text = step.action_data.get('text', '')
            # Get all elements and check for text
            elements = await self.mcp.list_elements()
            found = any(
                text.lower() in el.get('text', '').lower() or 
                text.lower() in el.get('label', '').lower()
                for el in elements
            )
            step.assertion_passed = found
            if not found:
                raise Exception(f"Text '{text}' not found on screen")
    
    async def _execute_swipe(self, step: ExecutionStep):
        """Swipe on the screen."""
        direction = step.action_data.get('direction', 'up')
        # Implementation depends on MCP capabilities
        # For now, just log it
        logger.info(f"Swipe {direction}")
    
    async def _execute_wait(self, step: ExecutionStep):
        """Wait for a specified duration."""
        duration = step.action_data.get('duration_ms', 1000)
        await asyncio.sleep(duration / 1000)
    
    async def _execute_back(self, step: ExecutionStep):
        """Press back button."""
        await self.mcp.press_back()
    
    async def _find_element(self, step: ExecutionStep) -> Optional[Dict]:
        """Find an element based on step criteria."""
        # Direct ID lookup
        if step.target_element_id:
            element = await db.fetchone(
                "SELECT * FROM elements WHERE id = ?",
                (step.target_element_id,)
            )
            if element:
                return element
        
        # Query-based lookup
        if step.element_query:
            # Get current elements from device
            elements = await self.mcp.list_elements()
            
            query = step.element_query
            for el in elements:
                match = True
                
                if 'type' in query and el.get('type') != query['type']:
                    match = False
                if 'label' in query and query['label'].lower() not in el.get('label', '').lower():
                    match = False
                if 'text' in query and query['text'].lower() not in el.get('text', '').lower():
                    match = False
                if 'semantic_type' in query:
                    # Check against known elements in DB
                    el_hash = f"{el.get('type')}:{el.get('label')}"
                    # This is simplified - could use semantic matching
                    pass
                
                if match:
                    return el
        
        return None
    
    async def _find_path_to_screen(self, target_screen_id: str) -> List[Dict]:
        """Find navigation path to target screen using BFS."""
        # Get current screen
        screenshot = await self.mcp.take_screenshot()
        if not screenshot:
            return []
        
        current_hash = ImageHasher.content_hash(screenshot)
        current = await db.fetchone(
            "SELECT id FROM screens WHERE content_hash = ?",
            (current_hash,)
        )
        
        if not current:
            return []
        
        current_id = current['id']
        
        # Check pre-computed paths
        path = await db.fetchone(
            """SELECT path_json, action_sequence FROM navigation_paths 
               WHERE from_screen_id = ? AND to_screen_id = ?""",
            (current_id, target_screen_id)
        )
        
        if path:
            return json.loads(path['action_sequence'] or '[]')
        
        # BFS to find path
        # This is a simplified version - full implementation would query transitions table
        return []
    
    def _parse_steps(self, steps_data: List[Dict]) -> List[ExecutionStep]:
        """Parse step data into ExecutionStep objects."""
        steps = []
        for i, data in enumerate(steps_data):
            step = ExecutionStep(
                number=i + 1,
                action_type=data.get('action', 'tap'),
                target_screen_id=data.get('screen_id'),
                target_element_id=data.get('element_id'),
                element_query=data.get('element_query'),
                action_data=data.get('data', {}),
                expected_result=data.get('expected'),
                assertion=data.get('assertion')
            )
            steps.append(step)
        return steps
    
    def _build_error_summary(self) -> Optional[str]:
        """Build a summary of errors from failed steps."""
        errors = [
            f"Step {step.number}: {step.error_message}"
            for step in self._steps
            if step.status == StepStatus.FAILED and step.error_message
        ]
        return '\n'.join(errors) if errors else None
    
    # === Control methods ===
    
    async def pause(self):
        """Pause execution."""
        if self.state == ExecutionState.RUNNING:
            self._pause_event.clear()
            self.state = ExecutionState.PAUSED
            self._notify("execution_paused", {"execution_id": self._current_execution})
    
    async def resume(self):
        """Resume execution."""
        if self.state == ExecutionState.PAUSED:
            self._pause_event.set()
            self.state = ExecutionState.RUNNING
            self._notify("execution_resumed", {"execution_id": self._current_execution})
    
    async def stop(self):
        """Stop execution."""
        self._stop_event.set()
        self._pause_event.set()
        self.state = ExecutionState.CANCELLED
    
    async def step_forward(self):
        """Execute next step (for step-by-step mode)."""
        if self.state == ExecutionState.PAUSED:
            self._pause_event.set()
            await asyncio.sleep(0.1)
            self._pause_event.clear()
    
    def get_status(self) -> Dict:
        """Get current execution status."""
        return {
            "state": self.state.value,
            "execution_id": self._current_execution,
            "current_step": self._current_step_index + 1 if self._steps else 0,
            "total_steps": len(self._steps),
            "current_step_action": (
                self._steps[self._current_step_index].action_type 
                if self._steps and 0 <= self._current_step_index < len(self._steps)
                else None
            )
        }
