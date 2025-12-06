import asyncio
import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Any

# Wrap imports in try/except to prevent crashes if manual_dinit is missing
try:
    from .manual_dinit import ServiceLoader, SimpleDinit
except ImportError:
    ServiceLoader = None
    SimpleDinit = None

logger = logging.getLogger(__name__)

# Configuration
TEST_MODE = os.environ.get("MCP_TESTING_MODE", "1") in ["1", "true"]
XFCE_STARTUP_DELAY = 0
CHROMIUM_STARTUP_DELAY = 0

async def start_dinit():
    """
    Starts background services (GUI, etc). 
    For Headless C++ tasks, we skip this if /etc/dinit.d doesn't exist.
    """
    dinit_dir = Path("/etc/dinit.d")
    
    if not dinit_dir.exists():
        logger.info("ℹ️ /etc/dinit.d not found. Skipping GUI service startup (Expected for Headless C++).")
        return

    if ServiceLoader is None:
        logger.warning("manual_dinit module not found. Skipping services.")
        return

    logger.info("Starting dinit services...")
    loader = ServiceLoader(dinit_dir)
    services = loader.load_all()
    if services:
        engine = SimpleDinit(services)
        engine.start("boot")
    else:
        logger.info("No services found to start.")

def subprocess_run(cmd, cwd=None):
    """Helper to run shell commands with logging."""
    try:
        # Run with shell=False for list args is safer and cleaner
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd)}\nStderr: {e.stderr}\nStdout: {e.stdout}")
        # We allow it to continue, as sometimes git warnings trigger this but aren't fatal

def setup_codebase(
    base: str,
    test: str,
    golden: str,
):
    """
    Setup the codebase: Time Travel + Submodule Sync + Clean Build.
    """
    # 1. Get Project Directory
    project_dir = os.environ.get("REPO_PATH", "/home/ubuntu/repo")
    
    if not os.path.exists(project_dir):
        logger.error(f"❌ Repo path {project_dir} does not exist!")
        return

    logger.info(f"📂 Switching context to {project_dir}")
    os.chdir(project_dir)

    # 2. Time Travel: Checkout the buggy commit (Base)
    logger.info(f"🕰️ Time Traveling to Buggy Commit: {base}")
    subprocess_run(["git", "checkout", "-f", base])
    
    # 3. CRITICAL FIX: Sync Submodules
    # Transmission relies on submodules. When we change commits, we MUST update them.
    logger.info("🔄 Synchronizing Git Submodules...")
    subprocess_run(["git", "submodule", "update", "--init", "--recursive"])

    # 4. Test Injection: Checkout tests from the solution (Golden)
    if golden:
        logger.info(f"💉 Injecting Tests from Golden Commit: {golden}")
        subprocess_run(["git", "checkout", golden, "--", "tests/"])

    # 5. Clean Build
    # CMake gets confused if we change git history underneath it. We must start fresh.
    build_dir = Path(project_dir) / "build"
    
    if build_dir.exists():
        logger.info("🧹 Cleaning old build directory...")
        shutil.rmtree(build_dir)
    
    build_dir.mkdir(parents=True, exist_ok=True)

    logger.info("🛠️ Configuring CMake...")
    subprocess_run(
        [
            "cmake", 
            "-G", "Ninja", 
            "-DCMAKE_BUILD_TYPE=RelWithDebInfo", 
            "-DENABLE_GTK=OFF", 
            "-DENABLE_QT=OFF", 
            "-DENABLE_MAC=OFF", 
            "-DENABLE_TESTS=ON", 
            ".."
        ], 
        cwd=str(build_dir)
    )
    
    # 6. Initial Build
    # We build once here to ensure dependencies (libdeflate, etc.) are compiled 
    # before the agent starts. This prevents the linker errors you saw.
    logger.info("🏗️ Running initial build (compiling dependencies)...")
    subprocess_run(["ninja"], cwd=str(build_dir))

def start_dinit_script():
    """Entry point for the start_dinit script."""
    asyncio.run(start_dinit())

async def default_setup(template: dict[str, Any]) -> None:
    """Default setup function that initializes the environment for coding tasks."""
    logger.info("=== ENVIRONMENT SETUP DEBUG ===")
    logger.info(f"Template: {template}")

    await start_dinit()

    setup_codebase(
        base=template["base"],
        test=template["test"],
        golden=template["golden"],
    )
    
    logger.info("✅ Environment Setup Complete.")