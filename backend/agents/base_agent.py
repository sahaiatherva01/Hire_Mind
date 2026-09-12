"""
HireMind AI — Base Specialist Agent
Enforces standard output contract {result, evidence, confidence} and automatic RAG logging.
"""
import json
import time
from typing import Dict, Any, List, Optional, Union
from services.rag_service import retrieve as rag_retrieve, get_gemini_client
from services.supabase_client import supabase_service
from config import Config

try:
    from google.genai import types
except ImportError:
    types = None


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
        """
        Specialist agent retrieval utility.
        Automatically logs retrieval queries, target collections, and returned items.
        """
        results = rag_retrieve(
            query=query,
            collection=collection,
            top_k=top_k,
            filter_criteria=filter_criteria
        )

        log_entry = {
            "agent": self.agent_name,
            "collection": collection,
            "query_preview": str(query)[:120] if isinstance(query, str) else "vector_query",
            "top_k": top_k,
            "matched_ids": [r.get("id") for r in results],
            "similarity_scores": [r.get("similarity") for r in results],
            "timestamp": time.time()
        }
        self.retrieval_logs.append(log_entry)
        return results

    def generate_json(
        self,
        prompt: str,
        model: str = Config.DEFAULT_MODEL,
        max_output_tokens: int = 2000,
        fallback_json: Optional[dict] = None
    ) -> dict:
        """Helper to invoke Gemini with structured JSON output and fallback resilience."""
        client = get_gemini_client()
        if not client:
            if fallback_json is not None:
                return fallback_json
            raise RuntimeError(f"[{self.agent_name}] Gemini client is not initialized.")

        try:
            config = None
            if types:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=max_output_tokens
                )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )

            raw_text = (response.text or "").strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            return json.loads(raw_text)

        except Exception as e:
            print(f"[{self.agent_name}] Gemini call error: {e}")
            if fallback_json is not None:
                return fallback_json
            raise

    def build_agent_output(
        self,
        result: Any,
        citations: List[Any],
        reasoning: str,
        confidence: float = 0.95,
        entity_id: Optional[str] = None,
        entity_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Constructs the standard explainable agent response contract and logs to evaluations table.
        """
        output = {
            "result": result,
            "evidence": {
                "citations": citations,
                "reasoning": reasoning,
                "retrieval_logs": list(self.retrieval_logs)
            },
            "confidence": round(float(confidence), 2)
        }

        # Automatically log to evaluations table if entity_id is present
        if entity_id:
            supabase_service.log_evaluation(
                entity_type=entity_type,
                entity_id=str(entity_id),
                orchestrator=self.orchestrator_name,
                agent_name=self.agent_name,
                result_json=result if isinstance(result, dict) else {"value": result},
                evidence_json=output["evidence"],
                confidence=confidence,
                retrieval_logs=self.retrieval_logs
            )

        # Clear retrieval logs for next turn
        self.retrieval_logs = []
        return output
