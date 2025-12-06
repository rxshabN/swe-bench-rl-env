import git
import json

REPO_PATH = "env/transmission"

def mine_tasks():    
    try:
        repo = git.Repo(REPO_PATH)
    except Exception as e:
        print(f"❌ Error: Could not open repo at {REPO_PATH}. Error: {e}")
        return

    tasks = []
    
    for commit in repo.iter_commits('main', max_count=3000):
        msg = str(commit.message).lower()
        
        if any(k in msg for k in ["fix", "resolve", "close", "bug"]):
            
            stats = commit.stats.files
            files = [str(f) for f in stats.keys()]
            
            has_code = any(f.endswith(('.cc', '.h', '.cpp')) for f in files)
            has_test = any('tests/' in f for f in files)
            
            if has_code and has_test:
                tasks.append({
                    "task_id": f"transmission-{commit.hexsha[:7]}",
                    "buggy_commit": commit.parents[0].hexsha,
                    "golden_commit": commit.hexsha,
                    "message": commit.summary.strip(),
                    "files": files
                })

    print(f"✅ Found {len(tasks)} valid tasks.")
    
    output_file = "hud_tasks.json"
    with open(output_file, "w") as f:
        json.dump(tasks, f, indent=2)

if __name__ == "__main__":
    mine_tasks()