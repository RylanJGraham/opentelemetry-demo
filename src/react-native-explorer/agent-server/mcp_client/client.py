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
            if isinstance(result, str):
                parsed = json.loads(result)
                return parsed if isinstance(parsed, list) else parsed.get("elements", [])
        except Exception as e:
            logger.error(f"List elements failed: {e}")
        return []
    
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
            if "mobile_swipe_on_screen" in self._tools:
                await self._call_tool("mobile_swipe_on_screen", {
                    "startX": x1, "startY": y1, "endX": x2, "endY": y2
                })
            return True
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
