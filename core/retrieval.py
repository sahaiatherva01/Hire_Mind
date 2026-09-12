import os
import json
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import numpy as np

from config import Config
from db.client import db_client
from core.gemini import embed_text

_COLLECTION_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_EMBEDDINGS_CACHE: Dict[str, np.ndarray] = {}


def _load_and_index_collection(collection_name: str) -> List[Dict[str, Any]]:
    if collection_name in _COLLECTION_CACHE:
        return _COLLECTION_CACHE[collection_name]

    path_map = {
        "kb_interview_questions": Config.KB_INTERVIEW_QUESTIONS_PATH,
        "kb_skills_taxonomy": Config.KB_SKILLS_TAXONOMY_PATH,
        "kb_jd_corpus": Config.KB_JD_CORPUS_PATH,
        "kb_resume_best_practices": Config.KB_RESUME_BEST_PRACTICES_PATH,
        "kb_company_interview_style": Config.KB_COMPANY_INTERVIEW_STYLE_PATH,
    }

    file_path = path_map.get(collection_name)
    items = []
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            items = []

    vectors = []
    for item in items:
        if collection_name == "kb_interview_questions":
            search_str = f"{item.get('question_text', '')} Role: {item.get('role', '')} Skill: {item.get('skill', '')} Stage: {item.get('stage', '')}"
        elif collection_name == "kb_skills_taxonomy":
            name = item.get("canonical_skill") or item.get("canonical_name", "")
            synonyms = ", ".join(item.get("synonyms", []))
            adj = ", ".join([f"{k}:{v}" for k, v in item.get("adjacent_skills", {}).items()])
            search_str = f"{name} Category: {item.get('category', '')} Synonyms: {synonyms} Related: {adj} Description: {item.get('description', '')}"
        elif collection_name == "kb_jd_corpus":
            title = item.get("role_title") or item.get("title", "")
            skills = ", ".join(item.get("required_skills", []))
            search_str = f"{title} Seniority: {item.get('seniority', '')} Skills: {skills} Description: {item.get('raw_text', '')}"
        elif collection_name == "kb_resume_best_practices":
            desc = item.get("rule_description") or item.get("guidance", "")
            after = item.get("after_example", "")
            search_str = f"{desc} Category: {item.get('category', '')} Example: {after} Impact: {item.get('impact_explanation', '')}"
        elif collection_name == "kb_company_interview_style":
            rubric = ", ".join(item.get("culture_principles", []))
            search_str = f"{item.get('company_name', '')} Culture Principles: {rubric}"
        else:
            search_str = json.dumps(item)

        item["_search_text"] = search_str
        vec = embed_text(search_str)
        vectors.append(vec)

    _COLLECTION_CACHE[collection_name] = items
    if vectors:
        _EMBEDDINGS_CACHE[collection_name] = np.array(vectors, dtype=np.float32)
    else:
        _EMBEDDINGS_CACHE[collection_name] = np.zeros((0, 768), dtype=np.float32)

    return items


def retrieve(
    query_or_embedding: Optional[Union[str, List[float]]] = None,
    collection: str = "kb_interview_questions",
    top_k: int = 3,
    filter_criteria: Optional[Dict[str, Any]] = None,
    query: Optional[Union[str, List[float]]] = None
) -> List[Dict[str, Any]]:
    """
    Shared RAG retrieval across all modules.
    Executes Supabase pgvector RPC if available, or local cosine similarity calculation.
    """
    effective_query = query_or_embedding if query_or_embedding is not None else query
    if effective_query is None:
        return []

    if isinstance(effective_query, str):
        query_text = effective_query
        query_embedding = embed_text(query_text)
    else:
        query_embedding = effective_query
        query_text = ""

    # 1. Supabase pgvector RPC query when online
    if db_client.supabase:
        try:
            rpc_map = {
                "kb_interview_questions": "match_interview_questions",
                "kb_skills_taxonomy": "match_skills",
                "kb_jd_corpus": "match_jd_corpus",
                "kb_resume_best_practices": "match_resume_guidelines",
                "kb_company_interview_style": "match_company_styles",
            }
            rpc_name = rpc_map.get(collection)
            if rpc_name:
                rpc_args = {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.20,
                    "match_count": top_k
                }
                if filter_criteria and "stage" in filter_criteria and collection == "kb_interview_questions":
                    rpc_args["filter_stage"] = filter_criteria["stage"]

                res = db_client.supabase.rpc(rpc_name, rpc_args).execute()
                if res.data:
                    return [{
                        "source_collection": collection,
                        "doc_id": row.get("id") or str(idx),
                        "content": row.get("question_text") or row.get("canonical_name") or row.get("title") or row.get("rule_title") or row.get("company_name") or str(row),
                        "similarity": round(float(row.get("similarity", 0.0)), 4),
                        "raw_data": row
                    } for idx, row in enumerate(res.data)]
        except Exception:
            pass

    # 2. Local vector cosine similarity fallback
    items = _load_and_index_collection(collection)
    if not items or collection not in _EMBEDDINGS_CACHE or len(_EMBEDDINGS_CACHE[collection]) == 0:
        return []

    item_embeddings = _EMBEDDINGS_CACHE[collection]
    q_vec = np.array(query_embedding, dtype=np.float32)
    q_norm = np.linalg.norm(q_vec)

    if q_norm == 0:
        return []

    norms = np.linalg.norm(item_embeddings, axis=1)
    norms[norms == 0] = 1.0
    scores = np.dot(item_embeddings, q_vec) / (norms * q_norm)

    ranked_indices = np.argsort(scores)[::-1]
    results = []

    for idx in ranked_indices:
        if len(results) >= top_k:
            break
        item = items[idx]
        sim_score = float(scores[idx])

        # Apply optional metadata filtering
        if filter_criteria:
            match = True
            for k, v in filter_criteria.items():
                if k in item and item[k] != v:
                    match = False
                    break
            if not match:
                continue

        content_str = (
            item.get("question_text") or
            item.get("canonical_skill") or
            item.get("canonical_name") or
            item.get("role_title") or
            item.get("title") or
            item.get("rule_description") or
            item.get("rule_title") or
            item.get("company_name") or
            item.get("_search_text", "")
        )

        results.append({
            "source_collection": collection,
            "doc_id": item.get("id") or str(idx),
            "content": content_str,
            "similarity": round(sim_score, 4),
            "raw_data": {k: v for k, v in item.items() if not k.startswith("_")}
        })

    return results
