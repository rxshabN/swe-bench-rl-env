import argparse
import json
import os
import subprocess
import sys
import time
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Error patterns that indicate infrastructure failure, not agent failure
INFRA_ERRORS = [
    "Connection closed",
    "McpError",
    "400 Bad Request",
    "500 Internal Server Error",
    "timeout",
    "timed out",
    "ConnectionRefused",
    "ClosedResourceError"
]

def evaluate_task_instance(task_id, run_index):
    """
    Executes a single instance of a task and determines if it was:
    1. An Infrastructure Failure (crashed, timed out, network error)
    2. An Agent Failure (ran successfully but Score was 0)
    3. An Agent Success (ran successfully and Score > 0)
    """
    start_time = time.time()
    
    # We use 'hud eval' command line
    cmd = [
        "hud", "eval", "pipeline_benchmark.json",
        "--task-ids", task_id,
        "--agent", "claude",
        "--yes",
        "--verbose"
    ]
    
    try:
        # Use shell=True on Windows, False on Linux/Mac
        use_shell = (os.name == 'nt')
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False, # We handle errors manually
            shell=use_shell
        )
        
        duration = time.time() - start_time
        combined_logs = result.stdout + "\n" + result.stderr

        # --- CHECK 1: Explicit Infrastructure Errors ---
        # If the tool crashed or printed specific error codes
        if result.returncode != 0:
            return task_id, "INFRA_FAIL", duration
            
        for err in INFRA_ERRORS:
            if err in combined_logs:
                # Special case: "timeout" might be in the agent's test logs (which is fine).
                # We care if it's in the MCP/System logs. 
                # For safety in this filter script, we treat ANY string match as a drop signal
                # to be ultra-conservative for RL training data.
                return task_id, "INFRA_FAIL", duration

        # --- CHECK 2: Score Extraction ---
        # We look for "Score: X.XXXX" or "Package Score: X.XX"
        # The regex looks for "Score:" followed by whitespace and a float
        score_match = re.search(r'(?:Score|Package Score):\s+([\d\.]+)', combined_logs)
        
        if not score_match:
            # If the process finished but didn't print a score, the grading runner crashed silently.
            return task_id, "INFRA_FAIL", duration
        
        try:
            score = float(score_match.group(1))
        except ValueError:
             return task_id, "INFRA_FAIL", duration

        # --- CHECK 3: Verdict ---
        if score > 0.0:
            return task_id, "AGENT_SUCCESS", duration
        else:
            return task_id, "AGENT_FAIL", duration

    except Exception as e:
        # Python script level crashes
        print(f"❌ Critical Executor Error on {task_id}: {e}")
        return task_id, "INFRA_FAIL", 0

def main():
    parser = argparse.ArgumentParser(description="Filter tasks for RL training.")
    parser.add_argument("--repeats", type=int, default=5, help="Times to run each task")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent cloud jobs")
    parser.add_argument("--input", default="hud_tasks.json", help="Source raw tasks file")
    args = parser.parse_args()

    if not os.path.exists("pipeline_benchmark.json"):
        print("❌ Error: pipeline_benchmark.json not found. Run generate_benchmark.py first.")
        sys.exit(1)

    # 1. Load Data
    with open(args.input, "r") as f:
        raw_tasks = json.load(f)
    
    # Filter to only tasks defined in the benchmark
    with open("pipeline_benchmark.json", "r") as f:
        bench_tasks = json.load(f)
        valid_ids = set(t["id"] for t in bench_tasks)
        
    tasks_to_run = [t for t in raw_tasks if t["task_id"] in valid_ids]

    print(f"🚀 Starting Curation for {len(tasks_to_run)} tasks.")
    print(f"   Config: {args.repeats} repeats, {args.concurrency} concurrent.")
    print("   Goal: Find Stable environments where the Agent consistently FAILS.")

    # 2. Execute
    task_results = defaultdict(list)
    
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = []
        for task in tasks_to_run:
            t_id = task["task_id"]
            for i in range(args.repeats):
                futures.append(executor.submit(evaluate_task_instance, t_id, i))

        completed = 0
        total = len(futures)
        
        for future in as_completed(futures):
            t_id, status, dur = future.result()
            task_results[t_id].append(status)
            completed += 1
            
            # Formatting output
            icon = "❓"
            if status == "AGENT_SUCCESS": icon = "✅" # Too easy
            elif status == "AGENT_FAIL":  icon = "📉" # Good hard task
            elif status == "INFRA_FAIL":  icon = "💥" # Bad env
            
            print(f"[{completed}/{total}] {icon} {t_id} ({dur:.1f}s) -> {status}")

    # 3. Filter and Save
    kept_tasks = []
    print("\n=== Filtering Results ===")
    
    for task in tasks_to_run:
        t_id = task["task_id"]
        results = task_results[t_id]
        
        total_runs = len(results)
        if total_runs == 0: continue

        infra_fails = results.count("INFRA_FAIL")
        agent_successes = results.count("AGENT_SUCCESS")
        agent_fails = results.count("AGENT_FAIL")

        # Criteria 1: Zero Tolerance for Infrastructure Instability
        if infra_fails > 0:
            print(f"DROP {t_id}: Infra unstable ({infra_fails}/{total_runs} failed)")
            continue
            
        # Criteria 2: Task must be "Hard" (Agent shouldn't solve it easily)
        # If agent solved it even once, it might be too easy or flaky.
        if agent_successes > 0:
            print(f"DROP {t_id}: Too easy ({agent_successes}/{total_runs} solved)")
            continue
            
        # Criteria 3: Task must be consistently failing (Score 0)
        if agent_fails == total_runs:
            print(f"KEEP {t_id}: Stable Failure (0/{total_runs} solved)")
            kept_tasks.append(task)

    output_file = "hud_tasks_final.json"
    with open(output_file, "w") as f:
        json.dump(kept_tasks, f, indent=2)

    print(f"\n✅ Saved {len(kept_tasks)} filtered tasks to {output_file}")

if __name__ == "__main__":
    main()