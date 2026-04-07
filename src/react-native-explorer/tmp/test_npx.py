import asyncio
import sys

async def test_npx():
    print(f"Testing npx.cmd from {sys.executable}")
    try:
        import os
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        process = await asyncio.create_subprocess_exec(
            npx_cmd, "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
        print(f"STDOUT: {stdout.decode().strip()}")
        print(f"STDERR: {stderr.decode().strip()}")
        print(f"Return code: {process.returncode}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_npx())
