import time
from typing import Dict, Any, List, Optional, Union

from config import Config
from db.client import db_client
from core.retrieval import retrieve as rag_retrieve
from core.gemini import generate_json, generate_text


class BaseAgent:
    def __init__(self, agent_name: str, orchestrator_name: str):
        self.agent_name = agent_name
        self.orchestrator_name = orchestrator_name
        self.retrieval_logs: List[Dict[str, Any]] = []

    def retrieve(
        self,
        query: Union[str, List[float]],
        collection: str,
        top_k: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        results = rag_retrieve(
            query_or_embedding=query,
            collection=collection,
            top_k=top_k,
            filter_criteria=filter_criteria
        )
        self.retrieval_logs.append({
            "agent": self.agent_name,
            "collection": collection,
            "query": str(query)[:120],
            "top_k": top_k,
            "count": len(results),
            "timestamp": time.time()
        })
        return results

    def generate_json_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        fallback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        result = generate_json(prompt, system_instruction=system_instruction)
        if result is not None:
            return result
        return fallback or {}

    def format_output(
        self,
        result: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        confidence: float,
        input_summary: str = "",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enforces the platform-wide contract:
        { "result": ..., "evidence": [...], "confidence": float }
        and persists audit records to the evaluations table.
        """
        confidence_clamped = max(0.0, min(1.0, float(confidence)))

        evidence_formatted = []
        for ev in evidence:
            evidence_formatted.append({
                "source_collection": ev.get("source_collection", "unknown"),
                "doc_id": ev.get("doc_id", "doc_0"),
                "content": str(ev.get("content", ""))[:400],
                "similarity": round(float(ev.get("similarity", 1.0)), 4)
            })

        output = {
            "result": result,
            "evidence": evidence_formatted,
            "confidence": confidence_clamped
        }

        # Log audit record
        db_client.log_evaluation(
            agent_name=self.agent_name,
            module=self.orchestrator_name,
            input_summary=input_summary or f"{self.agent_name} run",
            result=result,
            evidence=evidence_formatted,
            confidence=confidence_clamped,
            user_id=user_id,
            session_id=session_id
        )

        return output
