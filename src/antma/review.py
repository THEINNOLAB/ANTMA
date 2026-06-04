"""Review runner for candidate policy gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from antma.candidates import apply_gate_result, candidate_files_for_review, load_candidate
from antma.gates import GateEngine
from antma.policy import load_project_policy


def run_review(
    root: Path,
    candidate_id: Optional[str] = None,
    run_all: bool = False,
    policy_name: str = "default",
) -> List[Dict[str, Any]]:
    root = root.resolve()
    policy = load_project_policy(root, policy_name)
    engine = GateEngine(policy, root=root)
    results: List[Dict[str, Any]] = []
    for path in candidate_files_for_review(root, candidate_id=candidate_id, run_all=run_all):
        data = load_candidate(path)
        from_status = data["status"]
        gate_result = engine.evaluate(data)
        apply_gate_result(root, path, gate_result)
        results.append(
            {
                "candidate_id": data["candidate_id"],
                "from_status": from_status,
                "to_status": gate_result.status,
                "reason_code": gate_result.reason_code,
                "next_action": gate_result.next_action,
                "messages": list(gate_result.messages),
            }
        )
    return results
