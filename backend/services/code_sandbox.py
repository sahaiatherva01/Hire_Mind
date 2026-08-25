"""
Code Sandbox — executes candidate Python solutions against test cases.

MVP implementation: subprocess isolation with CPU/memory/time limits and no
network or filesystem access beyond a throwaway temp dir. This is adequate
for a local prototype but is NOT a production-grade sandbox.

Before real deployment (Phase 14, Security & Testing), replace the subprocess
call with a container-per-run (gVisor/Firecracker/Docker --network=none,
--read-only, seccomp profile) or a hosted judge API. The interface
(`run_solution`) is designed to stay the same either way.
"""
import json
import os
import resource
import subprocess
import sys
import tempfile
import textwrap

TIME_LIMIT_SECONDS = 5
MEMORY_LIMIT_MB = 256

_RUNNER_TEMPLATE = """
import json, sys

{user_code}

_ENTRY = {entry!r}
_tests = json.loads({tests_json!r})
_results = []
for t in _tests:
    try:
        out = globals()[_ENTRY](**t["input"])
        _results.append({{"output": out, "error": None}})
    except Exception as e:
        _results.append({{"output": None, "error": str(e)}})

print("@@HIREMIND_RESULT@@")
print(json.dumps(_results))
"""


def _limit_resources():
    """Applied via preexec_fn in the child process: caps CPU time & memory."""
    resource.setrlimit(resource.RLIMIT_CPU, (TIME_LIMIT_SECONDS, TIME_LIMIT_SECONDS))
    mem_bytes = MEMORY_LIMIT_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    # No core dumps, no forking extra processes, no new files beyond the script
    resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))


def _entry_function_name(function_signature):
    # "def two_sum(nums, target):" -> "two_sum"
    return function_signature.split("def ", 1)[1].split("(", 1)[0].strip()


def run_solution(user_code, function_signature, public_tests, hidden_tests):
    """
    Runs user_code against public + hidden tests in an isolated subprocess.
    Returns: { public_results, hidden_results, error }
    Each result item: { passed: bool, hidden: bool, expected, actual, error }
    """
    entry = _entry_function_name(function_signature)
    all_tests = [dict(t, hidden=False) for t in public_tests] + \
                [dict(t, hidden=True) for t in hidden_tests]

    script = _RUNNER_TEMPLATE.format(
        user_code=textwrap.indent(user_code, ""),
        entry=entry,
        tests_json=json.dumps(all_tests),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "solution.py")
        with open(script_path, "w") as f:
            f.write(script)

        try:
            proc = subprocess.run(
                [sys.executable, "-I", script_path],  # -I: isolated mode, ignores env/site
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=TIME_LIMIT_SECONDS + 2,
                preexec_fn=_limit_resources if hasattr(os, "fork") else None,
                env={"PATH": os.environ.get("PATH", "")},
            )
        except subprocess.TimeoutExpired:
            return {"error": "Time limit exceeded.", "public_results": [], "hidden_results": []}

        if "@@HIREMIND_RESULT@@" not in proc.stdout:
            err = proc.stderr.strip() or "Execution failed (no output)."
            return {"error": err[:2000], "public_results": [], "hidden_results": []}

        raw_json = proc.stdout.split("@@HIREMIND_RESULT@@")[1].strip()
        try:
            results = json.loads(raw_json)
        except json.JSONDecodeError:
            return {"error": "Could not parse execution results.", "public_results": [], "hidden_results": []}

    public_results, hidden_results = [], []
    for test, result in zip(all_tests, results):
        passed = result["error"] is None and result["output"] == test["expected"]
        entry_item = {
            "passed": passed,
            "hidden": test["hidden"],
            "expected": None if test["hidden"] else test["expected"],
            "actual": None if test["hidden"] else result["output"],
            "error": result["error"],
        }
        (hidden_results if test["hidden"] else public_results).append(entry_item)

    return {"error": None, "public_results": public_results, "hidden_results": hidden_results}


def estimate_complexity_and_quality(user_code):
    """
    Lightweight static heuristic standing in for a full complexity analyzer /
    AI code review (spec section 11). Scores 0-100 on a few readable signals:
    nested-loop depth (as a rough proxy for time complexity), use of
    appropriate data structures, line count discipline, and docstring/naming.
    Replace with an LLM-based reviewer call in Phase 8+ for real depth.
    """
    lines = [l for l in user_code.splitlines() if l.strip()]
    nested_loop_depth = 0
    max_depth = 0
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith(("for ", "while ")):
            depth = indent // 4 + 1
            max_depth = max(max_depth, depth)

    complexity_score = {0: 60, 1: 90, 2: 70, 3: 50}.get(max_depth, 35)

    uses_good_structures = any(
        kw in user_code for kw in ("dict(", "{}", "set(", "collections", "heapq")
    )
    has_names = any(len(l.split("=")[0].strip()) > 2 for l in lines if "=" in l)
    quality_score = 60
    quality_score += 20 if uses_good_structures else 0
    quality_score += 10 if has_names else 0
    quality_score += 10 if len(lines) < 40 else 0
    quality_score = min(quality_score, 100)

    return {"complexity": complexity_score, "code_quality": quality_score}
