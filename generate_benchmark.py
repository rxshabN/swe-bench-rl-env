import argparse
import json
import os
from pathlib import Path

def create_rich_prompt(task):
    files = task.get("files", [])
    files_list = "\n".join([f"{f}" for f in files]) if files else "See repository"
    
    return f"""Task: {task['task_id']}
            Problem: {task['message']}

            Issue
            GitHub Issue: {task['message']}

            Bug Description
            The codebase has one or more bugs and requires fixes. Tests have been written that define the expected behavior. Currently these tests FAIL. You must write code to make the tests pass.

            Files to Modify
            {files_list}

            Instructions
            1. Build the project: cd /home/ubuntu/repo/build && ninja
            2. Run tests to see what's failing: ctest --output-on-failure
            3. Analyze the failing tests (look at assertions and test names).
            4. Find relevant source files in /home/ubuntu/repo/libtransmission/
            5. Implement the fix.
            6. Rebuild and verify: cd /home/ubuntu/repo/build && ninja

            IMPORTANT: Evaluation Rules
            - The tests define the expected behavior - use them as your specification
            - Write your fix based on understanding the code and tests
            - Do NOT search for solutions outside the codebase
            - When you are confident your fix is complete, call evaluate_tool (grade_problem)
            - The repository is available at: /home/ubuntu/repo
            """

def main():
    parser = argparse.ArgumentParser(description="Generate the benchmark JSON file.")
    parser.add_argument("--image", type=str, help="The HUD Cloud Image ID (from `hud push`).")
    args = parser.parse_args()

    source_file = "hud_tasks.json" 
    
    if not os.path.exists(source_file):
        print(f"❌ Error: {source_file} not found.")
        return

    with open(source_file, "r") as f:
        raw_tasks = json.load(f)

    benchmark_tasks = []
    cwd = Path.cwd().as_posix()

    print(f"Generating benchmark from {source_file}...")

    for t in raw_tasks:
        prompt_text = create_rich_prompt(t)

        if args.image:
            mcp_config = {
                "default": {
                    "url": "https://mcp.hud.ai/v3/mcp",
                    "headers": {
                        "Authorization": "Bearer ${HUD_API_KEY}", 
                        "Mcp-Image": args.image
                    }
                }
            }
        else:
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

    print(f"Successfully generated {output_file}")
    if args.image:
        print(f"Configured for Cloud Image: {args.image}")
    else:
        print(f"Configured for Local Docker")

if __name__ == "__main__":
    main()