import json
import os

# 1. Load your raw commit data
with open("hud_tasks.json", "r") as f:
    raw_tasks = json.load(f)

benchmark_tasks = []

for t in raw_tasks:
    # 2. Create the HUD Task Object
    task = {
        # This ID must match what is in transmission_tasks.py
        "id": t["task_id"],
        
        # The prompt the Agent sees
        "prompt": f"""You are working on task: {t['task_id']}

        DESCRIPTION:
        Fix the issue described: {t['message']}

        The environment is reset to the parent commit. Run tests to verify failure, then fix it.
        """,
        
        # 3. THE MISSING LINK: Tell HUD how to run your Docker container
        "mcp_config": {
            "local": {
                "command": "docker",
                "args": [
                    "run", 
                    "--rm", 
                    "-i", 
                    # Mount the evaluation folder so the container sees the generated tasks
                    "-v", f"{os.getcwd()}/src/hud_controller/extractors:/evaluation/src/hud_controller/extractors",
                    "hud-transmission-env" # Your image name
                ]
            }
        },
        
        # 4. The Tools to call immediately
        # This calls the function you registered in app.py
        "setup_tool": {
            "name": "setup_problem",
            "arguments": {"problem_id": t["task_id"]}
        },
        
        # This calculates the reward (0 or 1)
        "evaluate_tool": {
            "name": "grade_problem",
            "arguments": {"problem_id": t["task_id"]}
        }
    }
    benchmark_tasks.append(task)

# 5. Save as the final benchmark file
with open("transmission_benchmark.json", "w") as f:
    json.dump(benchmark_tasks, f, indent=2)

print(f"✅ Generated transmission_benchmark.json with {len(benchmark_tasks)} tasks.")