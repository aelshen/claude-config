"""Exercise the public cw commands with local Git, Codex, and GitHub fixtures."""

from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import unittest


SKILL = Path(__file__).resolve().parents[1]
CW = SKILL / "scripts" / "cw"
FOOTER = (
    "Do not run git commands that change state; the caller commits. "
    "You have no network: anything you need from GitHub is in .cw/. "
    "Finish by writing the result object."
)
LEDGER_FIELDS = {
    "id", "name", "repo", "worktree", "branch", "base", "mode", "model",
    "effort", "sandbox", "pid", "watchdog_pid", "session_id", "started",
    "ended", "status", "exit_code", "timeout_s", "brief", "result_path",
    "events_path",
}

FAKE_CODEX = '''#!/usr/bin/env python3
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

args = sys.argv[1:]
session = next((arg for arg in args if re.fullmatch(r"[0-9a-f-]{36}", arg)), str(uuid.uuid4()))
turn = "follow-up" if "resume" in args else "first"
record = {
    "argv": args,
    "cwd": os.getcwd(),
    "stdin_devnull": os.path.samestat(os.fstat(0), os.stat(os.devnull)),
    "pid": os.getpid(),
    "pgid": os.getpgrp(),
    "sid": os.getsid(0),
    "session": session,
    "context_files": [p.name for p in Path(".cw").iterdir()],
}
with open(os.environ["FAKE_CODEX_LOG"], "a") as log:
    print(json.dumps(record), file=log)

def emit(kind, **data):
    print(json.dumps({"type": kind, **data}), flush=True)

emit("thread.started", thread_id=session)
emit("turn.started")
print("fixture stderr", file=sys.stderr, flush=True)
behavior = os.environ.get("FAKE_CODEX_BEHAVIOR", "success")
if behavior == "sleep":
    child_lock = os.environ.get("FAKE_CODEX_CHILD_LOCK")
    if child_lock and os.fork() == 0:
        with open(child_lock, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            print("ready", file=lock, flush=True)
            while os.path.exists(child_lock):
                time.sleep(0.1)
        sys.exit(0)
    while True:
        time.sleep(60)
if behavior == "fail":
    emit("turn.failed", error={"message": "fixture failure"})
    sys.exit(1)

if os.environ.get("FAKE_CODEX_EDIT"):
    with Path("tracked.txt").open("a") as tracked:
        print("worker change", file=tracked)
report = {
    "status": "done",
    "summary": turn + " fixture report",
    "files_changed": [],
    "tests": {"cmd": "", "passed": 0, "failed": 0, "blocked_by_sandbox": []},
    "open_questions": [],
    "commits": [],
}
output_flag = "-o" if "-o" in args else "--output-last-message"
Path(args[args.index(output_flag) + 1]).write_text(json.dumps(report))
emit("item.completed", item={"id": "item_0", "type": "agent_message", "text": report["summary"]})
emit("turn.completed", usage={"input_tokens": 2, "cached_input_tokens": 0, "output_tokens": 1})
'''

FAKE_GH = '''#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
if "pr" in args:
    kind = "pr"
elif "issue" in args:
    kind = "issue"
else:
    sys.exit("unexpected fixture gh invocation: " + repr(args))
action, number = args[args.index(kind) + 1:][:2]
if os.getcwd() != os.environ["FAKE_GH_REPO"]:
    sys.exit("expected gh to run in the source repository")
if action == "diff" and kind == "pr":
    print("diff --git a/fixture.txt b/fixture.txt")
elif action == "view" and "--json" in args:
    data = {"title": "fixture " + kind, "body": "context for " + number, "comments": []}
    if kind == "pr":
        data["headRefName"] = "topic"
    if set(args[args.index("--json") + 1].split(",")) != set(data):
        sys.exit("unexpected gh view fields")
    print(json.dumps(data))
else:
    sys.exit("unexpected fixture gh invocation: " + repr(args))
'''


def option(argv, *names):
    for index, argument in enumerate(argv):
        key, equals, value = argument.partition("=")
        if key in names:
            return value if equals else argv[index + 1]
    return None


class WorkerCLI(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repo = self.root / "source repo"
        self.remote = self.root / "origin.git"
        self.home = self.root / "worker state"
        self.trace = self.root / "codex.jsonl"
        self.brief = self.root / "task brief.md"
        self.brief.write_text("Update the tracked file.\n")
        binaries = self.root / "bin"
        binaries.mkdir()
        for name, script in (("codex", FAKE_CODEX), ("gh", FAKE_GH)):
            executable = binaries / name
            executable.write_text(script)
            executable.chmod(0o755)
        self.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("GIT_", "CW_", "FAKE_CODEX_"))
        }
        self.env.update({
            "CW_HOME": str(self.home),
            "PATH": str(binaries) + os.pathsep + self.env["PATH"],
            "FAKE_CODEX_LOG": str(self.trace),
            "FAKE_GH_REPO": str(self.repo),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_ALLOW_PROTOCOL": "file",
            "GIT_TERMINAL_PROMPT": "0",
        })
        self.git(self.root, "init", "--bare", "-q", self.remote)
        self.git(self.root, "init", "-q", "-b", "main", self.repo)
        (self.repo / "tracked.txt").write_text("base\n")
        self.git(self.repo, "add", "tracked.txt")
        self.git(self.repo, "commit", "-qm", "base")
        self.git(self.repo, "remote", "add", "origin", self.remote)
        self.git(self.repo, "push", "-qu", "origin", "main")
        self.addCleanup(self.stop_running_jobs)

    def git(self, cwd, *args, check=True):
        proc = subprocess.run(
            ["git", "-c", "user.name=Test Fixture", "-c", "user.email=fixture@example.invalid", *args],
            cwd=cwd, env=self.env, capture_output=True, text=True, timeout=10,
        )
        if check:
            self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc

    def cw(self, *args, code=0, input_text=None):
        proc = subprocess.run(
            [CW, *args], cwd=self.root, env=self.env, input=input_text,
            capture_output=True, text=True, timeout=12,
        )
        if code is not None:
            self.assertEqual(proc.returncode, code, f"{args!r}\n{proc.stdout}\n{proc.stderr}")
        return proc

    def stop_running_jobs(self):
        for path in self.home.glob("*.json"):
            job = json.loads(path.read_text())
            if job["status"] == "running":
                self.cw("kill", job["id"], code=None)

    def start(self, *options):
        before = set(self.home.glob("*.json"))
        proc = self.cw("start", self.repo, "--brief", self.brief, *options, input_text="caller stdin\n")
        created = set(self.home.glob("*.json")) - before
        self.assertEqual(len(created), 1, proc.stdout)
        ledger = created.pop()
        job = json.loads(ledger.read_text())
        self.assertEqual(ledger.stem, job["id"])
        for value in (job["id"], job["worktree"], str(ledger)):
            self.assertIn(value, proc.stdout)
        return job["id"]

    def ledger(self, job_id):
        return json.loads((self.home / (job_id + ".json")).read_text())

    def status(self, job_id):
        return json.loads(self.cw("status", job_id, "--json").stdout)

    def wait_for(self, predicate):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.04)
        self.fail(f"Timed out waiting for {predicate.__name__}")

    def records(self):
        if not self.trace.exists():
            return []
        return [json.loads(line) for line in self.trace.read_text().splitlines()]

    def finished(self, job_id):
        self.wait_for(lambda: self.ledger(job_id)["status"] != "running")
        self.assertEqual(self.ledger(job_id)["status"], "done")

    def assert_gone(self, pid):
        def process_gone():
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            return False
        self.wait_for(process_gone)

    def test_detached_start_and_clean_lifecycle(self):
        self.env["FAKE_CODEX_BEHAVIOR"] = "sleep"
        # This common override of global ignores also takes precedence over info/exclude.
        (self.repo / ".gitignore").write_text("!*\n")
        self.git(self.repo, "add", ".gitignore")
        self.git(self.repo, "commit", "-qm", "include files explicitly")
        self.git(self.repo, "push", "-q", "origin", "main")
        job_id = self.start("--name", "detachment check")
        self.wait_for(self.records)
        job = self.ledger(job_id)
        record = self.records()[0]
        self.assertTrue(LEDGER_FIELDS <= job.keys(), LEDGER_FIELDS - job.keys())
        self.assertEqual(job["name"], "detachment check")
        self.assertEqual(Path(job["repo"]), self.repo)
        worktree = self.repo.parent / f"cw-{self.repo.name}-{job_id}"
        self.assertEqual(Path(job["worktree"]), worktree)
        self.assertEqual(Path(record["cwd"]), worktree)
        self.assertEqual(job["base"], "origin/main")
        self.assertEqual(job["branch"], f"cw/{job_id}")
        self.assertEqual(self.git(worktree, "branch", "--show-current").stdout.strip(), job["branch"])
        self.assertEqual(job["timeout_s"], 3600)
        self.assertTrue(job["started"])
        self.assertIsNone(job["ended"])
        self.assertIsNone(job["exit_code"])
        self.assertEqual(job["status"], "running")
        self.assertEqual(Path(job["brief"]), worktree / ".cw" / "BRIEF.md")
        self.assertEqual(Path(job["result_path"]), worktree / ".cw" / "last.md")
        self.assertEqual(Path(job["events_path"]), worktree / ".cw" / "events.jsonl")
        self.assertTrue(record["stdin_devnull"])
        self.assertEqual([record["pid"], record["pgid"], record["sid"]], [job["pid"]] * 3)
        self.assertNotEqual(record["sid"], os.getsid(0))
        self.assertNotEqual(job["watchdog_pid"], job["pid"])
        self.assertNotEqual(os.getsid(job["watchdog_pid"]), os.getsid(0))
        brief = (worktree / ".cw" / "BRIEF.md").read_text()
        self.assertIn(self.brief.read_text().strip(), brief)
        self.assertTrue(brief.rstrip().endswith(FOOTER), brief)
        self.git(worktree, "check-ignore", "-q", ".cw/BRIEF.md")
        exclude = self.git(worktree, "rev-parse", "--git-path", "info/exclude").stdout.rstrip("\n")
        self.assertIn(".cw/", (worktree / exclude).read_text().splitlines())
        self.assertEqual(self.git(worktree, "status", "--short", "--", ".cw").stdout, "")
        self.assertIn("Read .cw/BRIEF.md and do the task it describes.", record["argv"])
        self.wait_for(lambda: self.status(job_id)["session_id"] == record["session"])
        self.cw("wait", job_id, "--max", "0", code=2)
        self.assertNotEqual(self.cw("clean", job_id, code=None).returncode, 0)
        self.assertTrue(worktree.is_dir())
        self.cw("kill", job_id)
        self.assert_gone(job["pid"])
        self.cw("wait", job_id, "--max", "0", code=1)
        self.assertEqual(self.status(job_id)["status"], "killed")
        self.cw("clean", job_id)
        self.assertFalse(worktree.exists())
        self.assertEqual(self.ledger(job_id)["status"], "cleaned")
        self.assertNotEqual(self.git(self.repo, "show-ref", "--verify", f"refs/heads/cw/{job_id}",
                                     check=False).returncode, 0)

    def test_mode_defaults_completed_status_and_wait(self):
        job_ids = []
        for mode, sandbox, effort in (("build", "workspace-write", "max"),
                                      ("review", "read-only", "high"),
                                      ("triage", "read-only", "high")):
            with self.subTest(mode=mode):
                job_id = self.start(*([] if mode == "build" else ["--mode", mode]))
                job_ids.append(job_id)
                self.cw("wait", job_id, "--max", "2")
                job = self.status(job_id)
                argv = self.records()[-1]["argv"]
                self.assertEqual((job["mode"], job["sandbox"], job["effort"]), (mode, sandbox, effort))
                self.assertEqual(option(argv, "--sandbox", "-s"), sandbox)
                self.assertIn("model_reasoning_effort=" + effort, [a.replace('"', "") for a in argv])
                self.assertIsNone(option(argv, "--model", "-m"))
                self.assertIsNone(job["model"])
                self.assertIn("--json", argv)
                schema = Path(option(argv, "--output-schema"))
                self.assertTrue((Path(job["worktree"]) / schema).is_file())
                self.assertEqual(job["status"], "done")
                self.assertEqual(job["exit_code"], 0)
                self.assertTrue(job["ended"])
                self.assertEqual(job["session_id"], self.records()[-1]["session"])
                self.assertEqual(job["last_events"], ["turn.started", "item.completed", "turn.completed"])
                self.assertEqual(job["summary"], "first fixture report")
                self.assertIn("fixture stderr", (Path(job["worktree"]) / ".cw" / "stderr.log").read_text())
                self.assertIn(job_id, self.cw("status").stdout)
        listed = json.loads(self.cw("status", "--json").stdout)
        self.assertEqual([job["id"] for job in listed], list(reversed(job_ids)))

    def test_failed_worker_and_stale_running_ledger(self):
        self.env["FAKE_CODEX_BEHAVIOR"] = "fail"
        job_id = self.start()
        self.cw("wait", job_id, "--max", "2", code=1)
        job = self.ledger(job_id)
        self.assertEqual((job["status"], job["exit_code"]), ("failed", 1))
        self.assert_gone(job["pid"])
        # Recreate the persisted state left by a supervisor lost before its final write.
        job.update(status="running", ended=None, exit_code=None)
        (self.home / (job_id + ".json")).write_text(json.dumps(job))
        self.assertEqual(self.status(job_id)["status"], "died")
        self.cw("wait", job_id, "--max", "0", code=1)
        self.assertEqual(self.ledger(job_id)["status"], "died")

    def test_watchdog_expires_without_a_waiter(self):
        self.env["FAKE_CODEX_BEHAVIOR"] = "sleep"
        child_lock = self.root / "descendant.lock"
        self.env["FAKE_CODEX_CHILD_LOCK"] = str(child_lock)
        job_id = self.start("--timeout", "1s")
        self.wait_for(lambda: child_lock.exists() and child_lock.read_text().strip() == "ready")
        self.wait_for(lambda: self.ledger(job_id)["status"] == "timed_out")
        self.assert_gone(self.records()[0]["pid"])
        # The OS releases the descendant's lock on death, even before an orphan is reaped.
        def descendant_exited():
            with child_lock.open() as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return False
            return True
        self.wait_for(descendant_exited)
        self.assertEqual(self.ledger(job_id)["timeout_s"], 1)
        self.cw("wait", job_id, "--max", "0", code=1)

    def test_resume_reuses_session_worktree_and_event_history(self):
        job_id = self.start("--mode", "review", "--model", "review-model")
        self.finished(job_id)
        first = self.ledger(job_id)
        events = Path(first["events_path"])
        original = events.read_bytes().rstrip(b"\n")
        events.write_bytes(original)
        message = "Review the caller's follow-up with spaces."
        self.cw("resume", job_id, message, "--timeout", "2m")
        self.cw("wait", job_id, "--max", "2")
        resumed = self.status(job_id)
        self.assertEqual(len(self.records()), 2)
        argv = self.records()[1]["argv"]
        self.assertIn("resume", argv)
        self.assertIn(first["session_id"], argv)
        self.assertIn(message, argv)
        first_argv = self.records()[0]["argv"]
        for flag in ("--sandbox", "-C", "-m", "-c", "-o", "--output-schema"):
            self.assertEqual(option(argv, flag), option(first_argv, flag))
        self.assertEqual(self.records()[1]["cwd"], first["worktree"])
        self.assertEqual(resumed["session_id"], first["session_id"])
        self.assertEqual(resumed["timeout_s"], 120)
        self.assertEqual(resumed["summary"], "follow-up fixture report")
        combined = events.read_bytes()
        self.assertTrue(original and combined.startswith(original + b"\n"))
        for line in combined.splitlines():
            self.assertIsInstance(json.loads(line), dict)
        self.assertIn(b"follow-up fixture report", combined[len(original):])

    def test_failed_resume_launch_preserves_previous_result(self):
        job_id = self.start()
        self.finished(job_id)
        first = self.ledger(job_id)
        result_path = Path(first["result_path"])
        original = result_path.read_bytes()
        empty_path = self.root / "without-codex"
        empty_path.mkdir()
        (empty_path / "python3").symlink_to(sys.executable)
        self.env["PATH"] = str(empty_path)
        self.cw("resume", job_id, "Follow up", code=1)
        self.assertEqual(self.ledger(job_id), first)
        self.assertEqual(result_path.read_bytes(), original)

    def test_simultaneous_resumes_start_one_worker(self):
        job_id = self.start()
        self.finished(job_id)
        self.env["FAKE_CODEX_BEHAVIOR"] = "sleep"
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = [pool.submit(self.cw, "resume", job_id, message, code=None)
                        for message in ("First follow-up", "Second follow-up")]
        self.assertEqual(sorted(attempt.result().returncode for attempt in attempts), [0, 1])
        self.wait_for(lambda: len(self.records()) == 2)
        self.cw("kill", job_id)
        self.assert_gone(self.records()[1]["pid"])

    def test_collect_shows_actual_changes_and_runs_test_in_worktree(self):
        self.env["FAKE_CODEX_EDIT"] = "1"
        job_id = self.start()
        self.finished(job_id)
        output = self.cw("collect", job_id).stdout
        self.assertIn("first fixture report", output)
        self.assertIn("M tracked.txt", output)
        self.assertIn("1 insertion", output)
        worktree = Path(self.ledger(job_id)["worktree"])
        code = ("from pathlib import Path\nPath('test-ran').touch()\n"
                "for i in range(35): print(f'outside-line-{i:02}')\nraise SystemExit(7)")
        command = shlex.join([sys.executable, "-c", code])
        proc = self.cw("collect", job_id, "--test", command, code=None)
        output = proc.stdout + proc.stderr
        self.assertTrue((worktree / "test-ran").is_file())
        self.assertFalse((self.repo / "test-ran").exists())
        self.assertNotIn("outside-line-00", output)
        self.assertIn("outside-line-05", output)
        self.assertIn("outside-line-34", output)
        self.assertRegex(output.lower(), r"(?:exit|return|status|rc)[\w\s:=()-]{0,20}\b7\b")
        self.assertEqual(self.status(job_id)["status"], "done")

    def test_collect_reports_pull_commands_for_local_clone_and_bundle(self):
        job_id = self.start()
        self.finished(job_id)
        job = self.ledger(job_id)
        clone = self.root / "scratch clone"
        self.git(self.root, "clone", "-q", "--branch", "main", self.remote, clone)
        self.git(clone, "checkout", "-qb", "returned-work")
        self.git(clone, "commit", "-q", "--allow-empty", "-m", "returned change")
        self.git(clone, "checkout", "-q", "main")
        bundle = Path(job["worktree"]) / ".cw" / "work.bundle"
        self.git(clone, "bundle", "create", bundle, "refs/heads/returned-work")
        export = self.root / "named export"
        export.write_bytes(bundle.read_bytes())
        report = Path(job["result_path"])
        data = json.loads(report.read_text())
        data["commits"] = [f"Caller can pull the change from `{clone}`.", str(export)]
        report.write_text(json.dumps(data))
        original = self.git(job["worktree"], "rev-parse", "HEAD").stdout
        output = self.cw("collect", job_id).stdout
        for artifact in (clone, bundle, export):
            self.assertIn(shlex.join(["git", "pull", "--ff-only", str(artifact), "returned-work"]), output)
        self.assertEqual(self.git(job["worktree"], "rev-parse", "HEAD").stdout, original)
        report.write_text("Raw worker notes.")
        self.assertIn("Raw worker notes.", self.cw("collect", job_id).stdout)

    def test_prefetch_model_and_explicit_options(self):
        self.env["CW_MODEL"] = "environment-model"
        self.git(self.repo, "push", "-q", "origin", "main:refs/heads/caller-owned")
        job_id = self.start("--mode", "review", "--effort", "max", "--branch", "caller-owned",
                            "--model", "explicit-model", "--prefetch", "pr:12", "issue:34")
        self.finished(job_id)
        job = self.ledger(job_id)
        record = self.records()[0]
        for name, marker in (("issue-34.md", "context for 34"), ("pr-12.md", "context for 12"),
                             ("pr-12.diff", "diff --git a/fixture.txt")):
            self.assertIn(name, record["context_files"])
            self.assertIn(marker, (Path(job["worktree"]) / ".cw" / name).read_text())
        self.assertEqual(job["model"], "explicit-model")
        self.assertEqual(option(record["argv"], "-m", "--model"), "explicit-model")
        self.assertEqual(job["effort"], "max")
        self.assertIn("model_reasoning_effort=max", [a.replace('"', "") for a in record["argv"]])
        self.cw("clean", job_id)
        self.git(self.repo, "show-ref", "--verify", "refs/heads/caller-owned")
        next_id = self.start()
        self.finished(next_id)
        self.assertEqual(self.ledger(next_id)["model"], "environment-model")
        self.assertEqual(option(self.records()[-1]["argv"], "-m", "--model"), "environment-model")

    def test_clean_preserves_unmerged_worker_commits(self):
        job_id = self.start()
        self.finished(job_id)
        job = self.ledger(job_id)
        worktree = Path(job["worktree"])
        (worktree / "caller.txt").write_text("caller commit\n")
        self.git(worktree, "add", "caller.txt")
        self.git(worktree, "commit", "-qm", "caller change")
        tip = self.git(worktree, "rev-parse", "HEAD").stdout
        self.cw("clean", job_id)
        self.assertFalse(worktree.exists())
        self.assertEqual(self.git(self.repo, "rev-parse", job["branch"]).stdout, tip)

    def test_clean_retries_after_worktree_was_removed(self):
        job_id = self.start()
        self.finished(job_id)
        job = self.ledger(job_id)
        self.git(self.repo, "worktree", "remove", "--force", job["worktree"])
        self.cw("clean", job_id)
        self.cw("clean", job_id)
        self.assertEqual(self.ledger(job_id)["status"], "cleaned")
        self.assertNotEqual(self.git(self.repo, "show-ref", "--verify", "refs/heads/" + job["branch"],
                                     check=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
