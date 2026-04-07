#!/usr/bin/env python3
import os, sys, json, time, hashlib, difflib, shutil

VCS_DIR = ".myvcs"
COMMITS_DIR = os.path.join(VCS_DIR, "commits")
LOG_FILE = os.path.join(VCS_DIR, "log.json")

def init():
    os.makedirs(COMMITS_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)
    print("Initialized empty repository")

def hash_commit(data):
    return hashlib.sha1(data.encode()).hexdigest()

def read_file(path):
    try:
        with open(path, "r", errors="ignore") as f:
            return f.readlines()
    except:
        return []

def write_file(path, lines):
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(path, "w") as f:
        f.writelines(lines)

def get_all_files():
    files = []
    for root, dirs, fs in os.walk("."):
        if VCS_DIR in root:
            continue
        for f in fs:
            files.append(os.path.relpath(os.path.join(root, f), "."))
    return files

def snapshot(commit_path):
    for file in get_all_files():
        dest = os.path.join(commit_path, file)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(file, dest)

def save(msg):
    if not os.path.exists(VCS_DIR):
        print("Not a repository")
        return

    with open(LOG_FILE, "r") as f:
        log = json.load(f)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_id = hash_commit(msg + timestamp)[:10]
    commit_path = os.path.join(COMMITS_DIR, commit_id)
    os.makedirs(commit_path)

    commit_data = {
        "id": commit_id,
        "message": msg,
        "time": timestamp,
        "type": "diff",
        "changes": {}
    }

    # FIRST COMMIT → FULL SNAPSHOT
    if not log:
        snapshot(commit_path)
        commit_data["type"] = "snapshot"
        commit_data["files"] = get_all_files()

    else:
        prev_commit = log[-1]["id"]
        prev_path = os.path.join(COMMITS_DIR, prev_commit)

        for file in get_all_files():
            new = read_file(file)
            old = read_file(os.path.join(prev_path, file))

            if new != old:
                diff = list(difflib.unified_diff(old, new, lineterm=""))
                commit_data["changes"][file] = diff

                save_path = os.path.join(commit_path, file + ".diff")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w") as f:
                    f.write("\n".join(diff))

    log.append(commit_data)

    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

    print(f"Saved commit {commit_id}")

def rebuild(commit_id, log):
    files = {}

    for c in log:
        cid = c["id"]
        cpath = os.path.join(COMMITS_DIR, cid)

        if c["type"] == "snapshot":
            for root, dirs, fs in os.walk(cpath):
                for f in fs:
                    rel = os.path.relpath(os.path.join(root, f), cpath)
                    files[rel] = read_file(os.path.join(root, f))

        else:
            for file, diff in c["changes"].items():
                old = files.get(file, [])
                patched = list(difflib.restore(diff, 1))
                files[file] = patched

        if cid == commit_id:
            break

    return files

def restore(commit_id):
    if not os.path.exists(LOG_FILE):
        print("No commits")
        return

    with open(LOG_FILE, "r") as f:
        log = json.load(f)

    files = rebuild(commit_id, log)

    # clear current working dir (except .myvcs)
    for root, dirs, fs in os.walk("."):
        if VCS_DIR in root:
            continue
        for f in fs:
            try:
                os.remove(os.path.join(root, f))
            except:
                pass

    for path, content in files.items():
        write_file(path, content)

    print(f"Restored to commit {commit_id}")

def log_cmd():
    if not os.path.exists(LOG_FILE):
        print("No commits")
        return

    with open(LOG_FILE, "r") as f:
        log = json.load(f)

    for c in reversed(log):
        print(f"\nCommit: {c['id']}")
        print(f"Message: {c['message']}")
        print(f"Time: {c['time']}")

def main():
    if len(sys.argv) < 2:
        return

    cmd = sys.argv[1]

    if cmd == "init":
        init()
    elif cmd == "save":
        msg = " ".join(sys.argv[2:])
        save(msg)
    elif cmd == "log":
        log_cmd()
    elif cmd == "restore":
        restore(sys.argv[2])

if __name__ == "__main__":
    main()
