import git
import json
import os

# PATH to your Transmission submodule
REPO_PATH = "env/transmission"

def mine_tasks():
    print(f"⛏️  Mining {REPO_PATH} for HUD-compatible tasks...")
    
    try:
        repo = git.Repo(REPO_PATH)
    except Exception as e:
        print(f"❌ Error: Could not open repo at {REPO_PATH}. Error: {e}")
        return

    tasks = []
    
    # We look at the last 3000 commits for high-quality examples
    for commit in repo.iter_commits('main', max_count=3000):
        msg = str(commit.message).lower()
        
        # Filter 1: Must be a "Fix" or "Close" (PR merge)
        if any(k in msg for k in ["fix", "resolve", "close", "bug"]):
            
            # Filter 2: Must touch C++ Code AND Tests
            stats = commit.stats.files
            files = [str(f) for f in stats.keys()]
            
            has_code = any(f.endswith(('.cc', '.h', '.cpp')) for f in files)
            has_test = any('tests/' in f for f in files)
            
            if has_code and has_test:
                # PARENT = The Buggy State (Before the fix)
                # CURRENT = The Golden State (The fix)
                tasks.append({
                    "task_id": f"transmission-{commit.hexsha[:7]}",
                    "buggy_commit": commit.parents[0].hexsha,
                    "golden_commit": commit.hexsha,
                    "message": commit.summary.strip(),
                    "files": files
                })

    print(f"✅ Found {len(tasks)} valid tasks.")
    
    # Save to JSON (HUD Template often uses a JSON dataset)
    output_file = "hud_tasks.json"
    with open(output_file, "w") as f:
        json.dump(tasks, f, indent=2)
    
    print(f"Saved to {output_file}. Here are the Top 3 candidates to show your boss:")
    for t in tasks[:3]:
        print(f"ID: {t['task_id']} | Msg: {t['message']}")

if __name__ == "__main__":
    mine_tasks()