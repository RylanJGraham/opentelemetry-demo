"""Mobile MCP Client for Android automation."""
import asyncio
import base64
import json
import logging
import shutil
import os
from contextlib import AsyncExitStack
from typing import Any, Optional, List, Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("agent.mcp")


class MCPClient:
    """Client for Mobile MCP server."""
    
    def __init__(self, package: str = "@mobilenext/mobile-mcp@latest"):
        self.package = package
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._tools: set[str] = set()
        self._device_id: Optional[str] = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._session is not None
    
    async def connect(self) -> bool:
        """Connect to MCP server."""
        try:
            logger.info("Connecting to MCP server...")
            
            # Find npx
            raw_cmd = "npx.cmd" if os.name == "nt" else "npx"
            npx_path = shutil.which(raw_cmd)
            if not npx_path:
                raise RuntimeError(f"Could not find '{raw_cmd}'")
            
            server_params = StdioServerParameters(
                command=npx_path,
                args=["-y", self.package],
                env=None,
            )
            
            self._exit_stack = AsyncExitStack()
            read, write = await asyncio.wait_for(
                self._exit_stack.enter_async_context(stdio_client(server_params)),
                timeout=60.0
            )
            
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self._session.initialize()
            
            # Discover tools
            tools_result = await self._session.list_tools()
            self._tools = {t.name for t in tools_result.tools}
            logger.info(f"MCP tools: {self._tools}")
            
            # Discover device
            await self._discover_device()
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            await self.disconnect()
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server."""
        self._connected = False
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception:
                pass
            self._exit_stack = None
        self._session = None
        logger.info("MCP disconnected")
    
    async def _discover_device(self):
        """Auto-discover Android device."""
        try:
            result = await self._call_tool("mobile_list_available_devices", {})
            if isinstance(result, str):
                data = json.loads(result)
                devices = data.get("devices", []) if isinstance(data, dict) else data
                if devices and len(devices) > 0:
                    device = devices[0]
                    self._device_id = device.get("id") or device.get("udid") or device.get("serial")
                    logger.info(f"Using device: {self._device_id}")
        except Exception as e:
            logger.warning(f"Device discovery failed: {e}")
    
    async def _call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call an MCP tool."""
        if not self._session:
            raise RuntimeError("Not connected")
        
        # Auto-add device argument
        args = dict(arguments)
        if self._device_id and "device" not in args:
            args["device"] = self._device_id
        
        result = await self._session.call_tool(tool_name, arguments=args)
        
        # Extract content
        if result.content:
            contents = []
            for item in result.content:
                if hasattr(item, "text"):
                    contents.append(item.text)
                elif hasattr(item, "data"):
                    contents.append(item.data)
            return contents[0] if len(contents) == 1 else contents
        return None
    
    # === High-level API ===
    
    async def take_screenshot(self) -> Optional[bytes]:
        """Capture screenshot as PNG bytes."""
        try:
            result = await self._call_tool("mobile_take_screenshot", {})
            if isinstance(result, str):
                # Handle base64
                if result.startswith("data:"):
                    result = result.split(",", 1)[1]
                return base64.b64decode(result.strip())
            elif isinstance(result, dict) and result.get("_type") == "image":
                return base64.b64decode(result["data"])
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
        return None
    
    async def list_elements(self) -> List[Dict]:
        """Get accessibility elements on screen."""
        try:
            result = await self._call_tool("mobile_list_elements_on_screen", {})
            if not result:
                logger.debug("No elements returned from MCP")
                return []
            
            if isinstance(result, str):
                result = result.strip()
                if not result:
                    return []
                
                # Handle "Found these elements on screen: [...]" format
                if "Found these elements" in result or "elements on screen" in result:
                    # Extract JSON array from the text
                    start_idx = result.find('[')
                    end_idx = result.rfind(']')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        result = result[start_idx:end_idx+1]
                    else:
                        logger.warning(f"Could not find JSON array in: {result[:200]}")
                        return []
                
                # Try to parse JSON
                try:
                    parsed = json.loads(result)
                    elements = parsed if isinstance(parsed, list) else parsed.get("elements", [])
                    # Normalize element coordinates
                    elements = [self._normalize_element(el) for el in elements if el]
                    logger.info(f"Parsed {len(elements)} elements from MCP")
                    return elements
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse elements JSON: {e}")
                    logger.debug(f"Raw result: {result[:200]}")
                    return []
                    
            elif isinstance(result, list):
                logger.info(f"Got {len(result)} elements as list")
                return [self._normalize_element(el) for el in result if el]
            elif isinstance(result, dict):
                elements = result.get("elements", [])
                logger.info(f"Got {len(elements)} elements from dict")
                return [self._normalize_element(el) for el in elements if el]
                
        except Exception as e:
            logger.error(f"List elements failed: {e}")
        return []
    
    def _normalize_element(self, el: Dict) -> Dict:
        """Normalize element coordinates from various MCP formats."""
        # Handle different coordinate formats
        x, y, width, height = 0, 0, 0, 0
        
        # Format 1: Direct x, y, width, height
        if 'x' in el and 'y' in el:
            x = int(el.get('x', 0))
            y = int(el.get('y', 0))
            width = int(el.get('width', 0))
            height = int(el.get('height', 0))
        
        # Format 2: coordinates dict
        elif 'coordinates' in el:
            coords = el['coordinates']
            if isinstance(coords, dict):
                x = int(coords.get('x', 0))
                y = int(coords.get('y', 0))
                width = int(coords.get('width', 0))
                height = int(coords.get('height', 0))
        
        # Format 3: bounds [x1, y1, x2, y2]
        elif 'bounds' in el:
            bounds = el['bounds']
            if isinstance(bounds, list) and len(bounds) >= 4:
                x = int(bounds[0])
                y = int(bounds[1])
                width = int(bounds[2]) - x
                height = int(bounds[3]) - y
        
        # Format 4: rect dict
        elif 'rect' in el:
            rect = el['rect']
            if isinstance(rect, dict):
                x = int(rect.get('left', rect.get('x', 0)))
                y = int(rect.get('top', rect.get('y', 0)))
                width = int(rect.get('width', 0))
                height = int(rect.get('height', 0))
        
        # Create normalized element
        normalized = dict(el)
        normalized['x'] = x
        normalized['y'] = y
        normalized['width'] = width
        normalized['height'] = height
        
        # Ensure label exists
        if not normalized.get('label'):
            normalized['label'] = normalized.get('text', '') or normalized.get('accessibilityLabel', '')
        
        # Ensure text exists  
        if not normalized.get('text'):
            normalized['text'] = normalized.get('label', '')
            
        return normalized
    
    async def tap(self, x: int, y: int) -> bool:
        """Tap at coordinates."""
        try:
            await self._call_tool("mobile_click_on_screen_at_coordinates", {"x": x, "y": y})
            return True
        except Exception as e:
            logger.error(f"Tap failed: {e}")
            return False
    
    async def swipe(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Swipe from (x1,y1) to (x2,y2)."""
        try:
            logger.info(f"Swiping from ({x1}, {y1}) to ({x2}, {y2})")
            
            # Try the swipe tool
            if "mobile_swipe_on_screen" in self._tools:
                result = await self._call_tool("mobile_swipe_on_screen", {
                    "startX": x1, "startY": y1, "endX": x2, "endY": y2
                })
                logger.debug(f"Swipe result: {result}")
                return True
            
            # Fallback: long press and drag if available
            logger.warning("Swipe tool not available, trying alternative")
            return False
            
        except Exception as e:
            logger.error(f"Swipe failed: {e}")
            return False
    
    async def press_back(self) -> bool:
        """Press Android back button."""
        try:
            if "mobile_press_button" in self._tools:
                await self._call_tool("mobile_press_button", {"button": "back"})
                return True
        except Exception as e:
            logger.error(f"Press back failed: {e}")
        return False
    
    async def type_text(self, text: str) -> bool:
        """Type text."""
        try:
            if "mobile_type_keys" in self._tools:
                await self._call_tool("mobile_type_keys", {"text": text})
                return True
        except Exception as e:
            logger.error(f"Type text failed: {e}")
        return False
    
    async def launch_app(self, package_name: str) -> bool:
        """Launch app by package name."""
        try:
            if "mobile_launch_app" in self._tools:
                await self._call_tool("mobile_launch_app", {"packageName": package_name})
                return True
        except Exception as e:
            logger.error(f"Launch app failed: {e}")
        return False
