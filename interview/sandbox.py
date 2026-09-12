import sys
import time
import json
import subprocess
from typing import Dict, Any, List


class CodeSandbox:
    @staticmethod
    def execute_code(user_code: str, test_cases: List[Dict[str, Any]], timeout_sec: int = 4) -> Dict[str, Any]:
        """
        Executes Python code against test cases in an isolated subprocess.
        """
        results = []
        passed_count = 0
        total_runtime_ms = 0.0

        for idx, tc in enumerate(test_cases):
            input_data = tc.get("input", {})
            expected = tc.get("expected")

            harness = f"""
import json, sys

{user_code}

def run_test():
    try:
        kwargs = {json.dumps(input_data)}
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

                out_str = proc.stdout.strip()
                if proc.returncode != 0 or not out_str:
                    err_msg = proc.stderr.strip() or "Process exited with error"
                    results.append({
                        "test_case": idx + 1,
                        "status": "Runtime Error",
                        "error": err_msg[:300],
                        "passed": False,
                        "runtime_ms": round(duration_ms, 2)
                    })
                    continue

                try:
                    out_json = json.loads(out_str.split("\n")[-1])
                except Exception:
                    out_json = {"error": f"Invalid output: {out_str[:150]}"}

                if "error" in out_json:
                    results.append({
                        "test_case": idx + 1,
                        "status": "Error",
                        "error": out_json["error"],
                        "passed": False,
                        "runtime_ms": round(duration_ms, 2)
                    })
                else:
                    actual = out_json.get("result")
                    passed = (actual == expected)
                    if passed:
                        passed_count += 1
                    results.append({
                        "test_case": idx + 1,
                        "status": "Passed" if passed else "Wrong Answer",
                        "actual": actual,
                        "expected": expected,
                        "passed": passed,
                        "runtime_ms": round(duration_ms, 2)
                    })

            except subprocess.TimeoutExpired:
                results.append({
                    "test_case": idx + 1,
                    "status": "Time Limit Exceeded",
                    "passed": False,
                    "runtime_ms": timeout_sec * 1000.0
                })

        total_cases = len(test_cases)
        correctness_pct = (passed_count / max(1, total_cases)) * 100.0

        return {
            "all_passed": passed_count == total_cases,
            "passed_count": passed_count,
            "total_cases": total_cases,
            "correctness_percentage": round(correctness_pct, 1),
            "total_runtime_ms": round(total_runtime_ms, 2),
            "test_results": results
        }
