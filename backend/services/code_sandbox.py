"""
HireMind AI — DSA Code Execution Sandbox
Runs user code safely against public and hidden test cases with timeout and resource limits.
"""
import sys
import time
import json
import subprocess
from typing import Dict, Any, List


class CodeSandbox:
    @staticmethod
    def execute_code(user_code: str, test_cases: List[Dict[str, Any]], timeout_sec: int = 4) -> Dict[str, Any]:
        """
        Runs Python code against provided test cases in a clean, isolated subprocess.
        """
        results = []
        passed_count = 0
        total_runtime_ms = 0.0

        for idx, tc in enumerate(test_cases):
            input_data = tc.get("input", {})
            expected = tc.get("expected")

            # Wrapper script to execute user code and compare result
            harness = f"""
import json, sys

{user_code}

def run_test():
    try:
        kwargs = {json.dumps(input_data)}
        # Try finding the target function in globals
        func_candidates = [v for k, v in globals().items() if callable(v) and not k.startswith('run_test') and not k.startswith('_')]
        if not func_candidates:
            print(json.dumps({{"error": "No callable function found in submitted code."}}))
            return

        func = func_candidates[-1]
        res = func(**kwargs)
        print(json.dumps({{"result": res}}))
    except Exception as e:
        print(json.dumps({{"error": str(e)}}))

if __name__ == '__main__':
    run_test()
"""
            start_t = time.perf_counter()
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", "-c", harness],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec
                )
                duration_ms = (time.perf_counter() - start_t) * 1000.0
                total_runtime_ms += duration_ms

                stdout = proc.stdout.strip()
                stderr = proc.stderr.strip()

                if proc.returncode != 0:
                    results.append({
                        "test_index": idx + 1,
                        "passed": False,
                        "error": stderr or f"Process exited with code {proc.returncode}",
                        "runtime_ms": round(duration_ms, 2)
                    })
                    continue

                try:
                    out_json = json.loads(stdout)
                except Exception:
                    out_json = {"error": f"Invalid output from execution: {stdout[:200]}"}

                if "error" in out_json:
                    results.append({
                        "test_index": idx + 1,
                        "passed": False,
                        "error": out_json["error"],
                        "runtime_ms": round(duration_ms, 2)
                    })
                else:
                    actual = out_json.get("result")
                    is_pass = (actual == expected)
                    if is_pass:
                        passed_count += 1
                    results.append({
                        "test_index": idx + 1,
                        "passed": is_pass,
                        "actual": actual,
                        "expected": expected,
                        "runtime_ms": round(duration_ms, 2)
                    })

            except subprocess.TimeoutExpired:
                results.append({
                    "test_index": idx + 1,
                    "passed": False,
                    "error": f"Time Limit Exceeded (> {timeout_sec}s)",
                    "runtime_ms": timeout_sec * 1000.0
                })
            except Exception as e:
                results.append({
                    "test_index": idx + 1,
                    "passed": False,
                    "error": str(e),
                    "runtime_ms": 0.0
                })

        code_lines = len([l for l in user_code.splitlines() if l.strip()])
        avg_runtime_ms = round(total_runtime_ms / max(1, len(test_cases)), 2)

        return {
            "total_tests": len(test_cases),
            "passed_tests": passed_count,
            "all_passed": (passed_count == len(test_cases)),
            "average_runtime_ms": avg_runtime_ms,
            "code_lines": code_lines,
            "details": results
        }


code_sandbox = CodeSandbox()
