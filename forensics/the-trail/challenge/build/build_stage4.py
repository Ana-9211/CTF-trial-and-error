"""Builds stage-4: a git repo where the real flag lives ONLY in a dangling
commit - orphaned so `git log --all` will NOT show it, recoverable only via
`git reflog` or `git fsck --lost-found`.

Technique:
  1. commit normal history
  2. commit the secret (flag) -> HEAD now points at it
  3. `git reset --hard HEAD~1` -> branch pointer moves back, the secret
     commit is now unreferenced by any branch or tag (dangling), but the
     reflog still records that HEAD was once there, and the objects survive
     until gc prunes them.
  4. keep committing normal history so the branch looks clean.

To ensure the dangling objects survive packaging, we disable auto-gc and
ship the whole .git directory (reflogs included).
"""
import os
import shutil
import subprocess

REPO = "aurora-config"
FLAG = "flag{wh1t3sp4ce_dns_m3m0ry_r3fl0g_full_ch41n_pwn3d}"


def run(cmd, cwd=None, capture=False):
    return subprocess.run(cmd, cwd=cwd, check=True, text=True,
                          stdout=(subprocess.PIPE if capture else subprocess.DEVNULL),
                          stderr=subprocess.DEVNULL)


def main():
    if os.path.exists(REPO):
        shutil.rmtree(REPO)
    os.makedirs(REPO)

    for c in [
        ["git", "init", "-q"],
        ["git", "config", "user.email", "ops@aurora.lab"],
        ["git", "config", "user.name", "Aurora Ops"],
        ["git", "config", "commit.gpgsign", "false"],
        ["git", "config", "gc.auto", "0"],          # never auto-gc away our dangling commit
        ["git", "config", "core.logAllRefUpdates", "true"],  # ensure reflog on
    ]:
        run(c, cwd=REPO)

    # commit 1: initial config
    with open(f"{REPO}/config.yaml", "w") as f:
        f.write("upstream: ingest.internal.lab:6514\nbatch_size: 1048576\n")
    run(["git", "add", "."], cwd=REPO)
    run(["git", "commit", "-q", "-m", "initial aurora config"], cwd=REPO)

    # commit 2: normal changelog
    with open(f"{REPO}/CHANGELOG.md", "w") as f:
        f.write("- initial release\n")
    run(["git", "add", "."], cwd=REPO)
    run(["git", "commit", "-q", "-m", "start changelog"], cwd=REPO)

    # commit 3: THE MISTAKE - secret committed
    with open(f"{REPO}/secrets.env", "w") as f:
        f.write(f"# DO NOT COMMIT\nUPSTREAM_TOKEN={FLAG}\n")
    run(["git", "add", "."], cwd=REPO)
    run(["git", "commit", "-q", "-m", "add upstream credentials for staging"], cwd=REPO)

    # capture the dangling commit hash for our own verification
    danglehash = run(["git", "rev-parse", "HEAD"], cwd=REPO, capture=True).stdout.strip()

    # commit 4: ORPHAN IT - reset branch back one commit. secret commit is now dangling.
    run(["git", "reset", "--hard", "HEAD~1"], cwd=REPO)

    # remove the file from the working tree too (reset --hard already did, but be explicit)
    if os.path.exists(f"{REPO}/secrets.env"):
        os.remove(f"{REPO}/secrets.env")

    # commit 5+: bury it under clean-looking history
    for msg in [
        "tune batch flush interval",
        "add health endpoint buffer occupancy",
        "docs: expand troubleshooting section",
    ]:
        with open(f"{REPO}/CHANGELOG.md", "a") as f:
            f.write(f"- {msg}\n")
        run(["git", "add", "."], cwd=REPO)
        run(["git", "commit", "-q", "-m", msg], cwd=REPO)

    # verification output
    all_log = run(["git", "log", "--oneline", "--all"], cwd=REPO, capture=True).stdout
    print("=== git log --oneline --all (secret commit should NOT appear) ===")
    print(all_log)
    print(f"dangling commit hash: {danglehash}")
    print(f"flag (orphaned)     : {FLAG}")


if __name__ == "__main__":
    main()
