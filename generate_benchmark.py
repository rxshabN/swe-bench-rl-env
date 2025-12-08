import argparse
import json
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Generate the benchmark JSON file.")
    parser.add_argument("--image", type=str, help="The HUD Cloud Image ID (from `hud push`).")
    args = parser.parse_args()

    # 1. Load your mined tasks
    # Ensure this points to your curated list if you have one, or the raw list
    source_file = "hud_tasks.json" 
    
    if not os.path.exists(source_file):
        print(f"❌ Error: {source_file} not found.")
        return

    with open(source_file, "r") as f:
        raw_tasks = json.load(f)

    benchmark_tasks = []
    cwd = Path.cwd().as_posix()

    print(f"🔨 Generating benchmark from {source_file}...")

    for t in raw_tasks:
        prompt_text = f"""You are a software engineer fixing an issue in the Transmission BitTorrent client (C++ codebase).

        TASK ID: {t['task_id']}
        ISSUE: {t['message']}

        REPOSITORY: /home/ubuntu/repo

        YOUR TASK:
        The codebase has one or more bugs and requires fixes. Tests have been written that define the expected behavior. Currently these tests FAIL. You must write code to make the tests pass.

        WORKFLOW:
        1. Build the project: cd /home/ubuntu/repo/build && ninja
        2. Run tests to see what's failing: ctest --output-on-failure
        3. Analyze the failing tests (look at assertions and test names).
        4. Find relevant source files in /home/ubuntu/repo/libtransmission/
        5. Implement the fix.
        6. Rebuild and verify: cd /home/ubuntu/repo/build && ninja

        IMPORTANT:
        - The tests define the expected behavior - use them as your specification
        - Write your fix based on understanding the code and tests
        - Do NOT search for solutions outside the codebase
        """

        if args.image:
            # --- CLOUD CONFIGURATION (CORRECTED) ---
            # According to HUD docs: Use the HUD Gateway URL + Headers
            mcp_config = {
                "hud": {
                    "url": "https://mcp.hud.ai/v3/mcp",
                    "headers": {
                        # The SDK automatically injects HUD_API_KEY if available, 
                        # but we can explicit or rely on env vars.
                        "Authorization": "Bearer ${HUD_API_KEY}", 
                        "Mcp-Image": args.image
                    }
                }
            }
        else:
            # --- LOCAL CONFIGURATION ---
            mcp_config = {
                "local": {
                    "command": "docker",
                    "args": [
                        "run", 
                        "--rm", 
                        "-i", 
                        "--network", "none",
                        "-v", f"{cwd}/src/hud_controller/extractors:/evaluation/src/hud_controller/extractors",
                        "swe-bench-rl-env:0.1.0"
                    ]
                }
            }

        task = {
            "id": t["task_id"],
            "prompt": prompt_text,
            "mcp_config": mcp_config,
            "setup_tool": {
                "name": "setup_problem",
                "arguments": {"problem_id": t["task_id"]}
            },
            "evaluate_tool": {
                "name": "grade_problem",
                "arguments": {"problem_id": t["task_id"]}
            }
        }
        benchmark_tasks.append(task)

    output_file = "transmission_benchmark.json"
    with open(output_file, "w") as f:
        json.dump(benchmark_tasks, f, indent=2)

    print(f"✅ Successfully generated {output_file}")
    if args.image:
        print(f"☁️  Configured for Cloud Image: {args.image}")
    else:
        print(f"💻 Configured for Local Docker")

if __name__ == "__main__":
    main()