import json
import os

with open("hud_tasks.json", "r") as f:
    tasks = json.load(f)

output_code = """from hud_controller.spec import EnvironmentState, Grade, problem
from hud_controller.graders import AgentPatchGrader

# AUTOMATICALLY GENERATED FROM hud_tasks.json
"""

for task in tasks:
    func_name = task['task_id'].replace("-", "_")
    safe_msg = task['message'].replace('"', "'")
    
    files_list = "\\n".join([f"- {f}" for f in task.get('files', [])])
    
    description = f"""Task: {task['task_id']}
    Problem: {safe_msg}

    Issue
    GitHub Issue: {safe_msg}

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
    - The repository is available at: /home/ubuntu/repo
    """

    task_code = f"""
@problem(
    id="{task['task_id']}",
    description=\"\"\"
{description}
    \"\"\",
    hints=[],
    difficulty="hard",
    task_type="coding",
    review_level="no-review",
    base="{task['buggy_commit']}",
    test="{task['golden_commit']}", 
    golden="{task['golden_commit']}",
)
def {func_name}(state: EnvironmentState) -> Grade:
    return Grade.from_subscores([
        AgentPatchGrader.grade(
            state=state,
            weight=1.0,
            base="{task['buggy_commit']}",
            test="{task['golden_commit']}", 
            golden="{task['golden_commit']}",
            jest_test_files={json.dumps(task['files'])}, 
        )
    ])
"""
    output_code += task_code

output_path = "src/hud_controller/extractors/transmission_tasks.py"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w") as f:
    f.write(output_code)

print(f"Generated {len(tasks)} tasks in {output_path}")