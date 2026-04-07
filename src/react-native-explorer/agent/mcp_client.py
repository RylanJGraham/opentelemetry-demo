"""
Mobile MCP Client — connects to the Mobile MCP server via stdio transport
to control an Android emulator.
"""

import asyncio
import base64
import json
import logging
import shutil
import os
from contextlib import AsyncExitStack
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .utils import ensure_adb_on_path

logger = logging.getLogger("explorer.mcp")


class MobileMCPClient:
    """
    Wraps the MCP Python SDK to communicate with @mobilenext/mobile-mcp.
    Spawns the MCP server as a child process via stdio transport.
    """

    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._tools: list[dict] = []
        self._tool_names: set[str] = set()
        self._device_id: Optional[str] = None

    async def connect(self):
        """Spawn the Mobile MCP server and establish a session."""
        import asyncio
        
        print("[EXPLORER] MCP: Initializing environment...", flush=True)
        # 🔧 Ensure ADB is available
        ensure_adb_on_path()

        logger.info("MCP: Starting connection...")
        print("[EXPLORER] MCP: Starting connection...", flush=True)

        # 🔧 On Windows, npx is a .cmd script, not an executable
        # Absolute path is required for reliability in asyncio subprocesses
        raw_cmd = "npx.cmd" if os.name == "nt" else "npx"
        npx_path = shutil.which(raw_cmd)
        
        if not npx_path:
            logger.error(f"Node tool '{raw_cmd}' not found on PATH")
            raise RuntimeError(f"Could not find '{raw_cmd}'. Is Node.js installed and on your PATH?")

        server_params = StdioServerParameters(
            command=npx_path,
            args=["-y", "@mobilenext/mobile-mcp@latest"],
            env=None,
        )
        print("[EXPLORER] MCP: Creating exit stack...", flush=True)

        self._exit_stack = AsyncExitStack()
        print("[EXPLORER] MCP: Entering stdio context (this may take 30s on first run)...", flush=True)
        
        # Add timeout for npx download on first run
        try:
            read, write = await asyncio.wait_for(
                self._exit_stack.enter_async_context(stdio_client(server_params)),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            print("[EXPLORER] MCP: Timeout connecting to MCP server (npx download too slow)", flush=True)
            raise RuntimeError("MCP connection timeout - npx may be downloading packages")
            
        print("[EXPLORER] MCP: Creating client session...", flush=True)
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        print("[EXPLORER] MCP: Initializing session...", flush=True)
        await self._session.initialize()
        print("[EXPLORER] MCP: Session initialized", flush=True)

        # Discover available tools
        print("[EXPLORER] MCP: Listing tools...", flush=True)
        tools_result = await self._session.list_tools()
        self._tools = [
            {"name": t.name, "description": t.description}
            for t in tools_result.tools
        ]
        self._tool_names = {t["name"] for t in self._tools}

        logger.info(f"MCP: Tools discovered: {', '.join(self._tool_names)}")
        print(f"[EXPLORER] MCP: Tools discovered: {', '.join(self._tool_names)}", flush=True)

        # Auto-discover device
        print("[EXPLORER] MCP: Discovering device...", flush=True)
        await self._discover_device()
        print("[EXPLORER] MCP: Device discovery complete", flush=True)

        return self._tools

    async def _discover_device(self):
        """Discover the first available device and store its ID."""
        try:
            result = await self._session.call_tool(
                "mobile_list_available_devices", arguments={}
            )
            if result.content:
                for item in result.content:
                    if hasattr(item, "text") and item.text:
                        text = item.text.strip()
                        logger.debug(f"Device list response: {text[:500]}")
                        # Try parsing as JSON
                        try:
                            data = json.loads(text)
                            # Unwrap {"devices": [...]} format
                            devices = None
                            if isinstance(data, dict) and "devices" in data:
                                devices = data["devices"]
                            elif isinstance(data, list):
                                devices = data
                            elif isinstance(data, dict):
                                # Single device object
                                self._device_id = (
                                    data.get("id")
                                    or data.get("udid")
                                    or data.get("serial")
                                )

                            if devices and len(devices) > 0:
                                device = devices[0]
                                if isinstance(device, dict):
                                    self._device_id = (
                                        device.get("id")
                                        or device.get("udid")
                                        or device.get("serial")
                                        or device.get("name")
                                    )
                                elif isinstance(device, str):
                                    self._device_id = device
                        except json.JSONDecodeError:
                            # Maybe it's a plain device ID string
                            if text and not text.startswith("MCP error"):
                                self._device_id = text.split("\n")[0].strip()

            if self._device_id:
                logger.info(f"📱 Using device: {self._device_id}")
            else:
                logger.warning("⚠️ No device found! Make sure an emulator is running.")
        except Exception as e:
            logger.error(f"Failed to discover device: {e}")

    async def disconnect(self):
        """Close the MCP session and stop the server process."""
        if self._exit_stack:
            try:
                # 🔧 Fix for Windows/AnyIO: Catch cancel-scope errors during shutdown
                await self._exit_stack.aclose()
            except RuntimeError as e:
                # Log quietly if it's just a context mismatch during cancellation
                if "cancel scope" not in str(e):
                    logger.warning(f"MCP disconnect error: {e}")
            finally:
                self._session = None
                self._exit_stack = None
                logger.info("🔌 Disconnected from Mobile MCP server")

    async def _call_tool(self, tool_name: str, arguments: dict = None) -> Any:
        """Call an MCP tool and return the result."""
        if not self._session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")

        if tool_name not in self._tool_names:
            # Try with mobile_ prefix
            prefixed = f"mobile_{tool_name}"
            if prefixed in self._tool_names:
                tool_name = prefixed
            else:
                raise ValueError(
                    f"Tool '{tool_name}' not found. Available: {self._tool_names}"
                )

        # Auto-inject device argument if we have one and it's not already set
        args = dict(arguments or {})
        if self._device_id and "device" not in args:
            args["device"] = self._device_id

        logger.debug(f"Calling MCP tool: {tool_name}({args})")
        result = await self._session.call_tool(tool_name, arguments=args)

        # Extract content from result
        if result.content:
            contents = []
            for item in result.content:
                item_type = getattr(item, "type", None)
                logger.debug(
                    f"  Content item: type={item_type}, "
                    f"attrs={[a for a in dir(item) if not a.startswith('_')]}"
                )

                if item_type == "image" or hasattr(item, "mimeType"):
                    # ImageContent — .data is base64, .mimeType is e.g. "image/png"
                    data = getattr(item, "data", None)
                    mime = getattr(item, "mimeType", "image/png")
                    if data:
                        contents.append({"_type": "image", "data": data, "mimeType": mime})
                    else:
                        logger.warning(f"  ImageContent with no data: {item}")
                elif hasattr(item, "text"):
                    contents.append(item.text)
                elif hasattr(item, "data"):
                    contents.append(item.data)
                else:
                    logger.warning(f"  Unknown content item: {item}")

            if len(contents) == 1:
                return contents[0]
            return contents

        return None

    async def _call_tool_raw(self, tool_name: str, arguments: dict = None) -> Any:
        """Call an MCP tool and return the raw result object for inspection."""
        if not self._session:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        return await self._session.call_tool(tool_name, arguments=arguments or {})

    # ── High-level API ───────────────────────────────────────────────

    async def take_screenshot(self) -> Optional[bytes]:
        """Capture a screenshot of the current emulator screen.
        Returns raw PNG bytes."""
        try:
            result = await self._call_tool("mobile_take_screenshot")
            if result is None:
                logger.error("Screenshot returned None")
                return None

            logger.debug(f"Screenshot result type: {type(result)}, "
                        f"preview: {str(result)[:200] if isinstance(result, str) else '(dict/bytes)'}")

            # Check for MCP error responses (returned as text)
            if isinstance(result, str) and result.startswith("MCP error"):
                logger.error(f"Screenshot MCP error: {result}")
                return None

            # Case 1: ImageContent dict from our _call_tool
            if isinstance(result, dict) and result.get("_type") == "image":
                b64_data = result["data"]
                return base64.b64decode(b64_data)

            # Case 2: Raw base64 string
            if isinstance(result, str):
                # Strip data URI prefix if present
                if result.startswith("data:"):
                    result = result.split(",", 1)[1]
                # Strip any whitespace/newlines
                result = result.strip()
                try:
                    return base64.b64decode(result)
                except Exception as e:
                    logger.error(f"Failed to decode base64 screenshot: {e}")
                    return None

            # Case 3: Already bytes
            if isinstance(result, bytes):
                return result

            # Case 4: List of content items (pick the image one)
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and item.get("_type") == "image":
                        return base64.b64decode(item["data"])
                    if isinstance(item, str):
                        try:
                            return base64.b64decode(item.strip())
                        except Exception:
                            continue
                logger.error(f"No image found in list result: {[type(i) for i in result]}")
                return None

            logger.error(f"Unexpected screenshot result type: {type(result)}")
            return None
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    async def execute_action(self, action: dict) -> bool:
        """Execute a general exploration action.
        The action dictionary should contain 'action_type' and either 'x','y' or 'element_id'.
        """
        action_type = action.get("action_type") or action.get("action", "tap")
        
        try:
            if action_type == "tap":
                x = action.get("x")
                y = action.get("y")
                if x is not None and y is not None:
                    return await self.tap(int(x), int(y))
                else:
                    logger.error(f"Cannot tap: coordinates missing in {action}")
                    return False
                    
            elif action_type == "type":
                text = action.get("text") or action.get("value", "")
                return await self.type_text(text)
                
            elif action_type == "swipe":
                x1, y1 = action.get("x1", 0), action.get("y1", 0)
                x2, y2 = action.get("x2", 0), action.get("y2", 0)
                return await self.swipe(x1, y1, x2, y2)
                
            elif action_type == "back":
                return await self.press_back()
                
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")
            return False

    async def list_elements(self) -> list[dict]:
        """Get the accessibility tree / element list from the current screen.
        Returns a list of UI elements with their properties."""
        try:
            result = await self._call_tool("mobile_list_elements_on_screen")
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list):
                        return parsed
                    elif isinstance(parsed, dict):
                        return parsed.get("elements", [parsed])
                except json.JSONDecodeError:
                    # Return raw text as a single element
                    return [{"type": "raw", "text": result}]
            elif isinstance(result, list):
                return result
            return []
        except Exception as e:
            logger.error(f"Failed to list elements: {e}")
            return []

    async def tap(self, x: int, y: int) -> bool:
        """Tap at specific coordinates on the screen."""
        try:
            await self._call_tool(
                "mobile_click_on_screen_at_coordinates",
                {"x": x, "y": y},
            )
            logger.debug(f"👆 Tapped at ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"Failed to tap at ({x}, {y}): {e}")
            return False

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Perform a swipe gesture."""
        try:
            # Try the swipe tool if available
            tool_name = None
            for name in ["mobile_swipe_on_screen", "mobile_swipe"]:
                if name in self._tool_names:
                    tool_name = name
                    break

            if tool_name:
                await self._call_tool(
                    tool_name,
                    {"startX": x1, "startY": y1, "endX": x2, "endY": y2, "duration": duration_ms},
                )
            else:
                # Fallback: no swipe tool, log warning
                logger.warning("Swipe tool not available in MCP server")
                return False

            logger.debug(f"👆 Swiped from ({x1},{y1}) to ({x2},{y2})")
            return True
        except Exception as e:
            logger.error(f"Failed to swipe: {e}")
            return False

    async def press_back(self) -> bool:
        """Press the Android back button."""
        try:
            # The MCP server uses mobile_press_button with button name
            if "mobile_press_button" in self._tool_names:
                await self._call_tool("mobile_press_button", {"button": "back"})
                logger.debug("⬅️  Pressed back button")
                return True

            # Fallback: try other tool names
            for name in ["mobile_press_back", "mobile_go_back", "mobile_back"]:
                if name in self._tool_names:
                    await self._call_tool(name)
                    logger.debug("⬅️  Pressed back button")
                    return True

            logger.warning("No back button tool available")
            return False
        except Exception as e:
            logger.error(f"Failed to press back: {e}")
            return False

    async def type_text(self, text: str) -> bool:
        """Type text into the currently focused input field."""
        try:
            # The MCP server uses mobile_type_keys
            if "mobile_type_keys" in self._tool_names:
                await self._call_tool("mobile_type_keys", {"text": text})
                logger.debug(f"⌨️  Typed: {text}")
                return True

            for name in ["mobile_type_text", "mobile_input_text", "mobile_type"]:
                if name in self._tool_names:
                    await self._call_tool(name, {"text": text})
                    logger.debug(f"⌨️  Typed: {text}")
                    return True

            logger.warning("No type text tool available")
            return False
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False

    async def press_home(self) -> bool:
        """Press the home button."""
        try:
            for name in ["mobile_press_home", "mobile_go_home", "mobile_home"]:
                if name in self._tool_names:
                    await self._call_tool(name)
                    logger.debug("🏠 Pressed home button")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to press home: {e}")
            return False

    async def launch_app(self, package_name: str) -> bool:
        """Launch an app by package name."""
        try:
            for name in ["mobile_launch_app", "mobile_open_app"]:
                if name in self._tool_names:
                    await self._call_tool(name, {"packageName": package_name})
                    logger.debug(f"🚀 Launched app: {package_name}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to launch app: {e}")
            return False

    @property
    def available_tools(self) -> list[dict]:
        """Return list of available MCP tools."""
        return self._tools

    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._session is not None
