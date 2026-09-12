"""
HireMind AI — Shared RAG Retrieval & Embedding Service
Grounds all agents across Modules A, B, and C in real pgvector knowledge collections.
"""
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from config import Config
from services.supabase_client import supabase_service

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# In-memory vector index cache for local / fallback execution
_COLLECTION_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_EMBEDDINGS_CACHE: Dict[str, np.ndarray] = {}
_GEMINI_CLIENT = None


def get_gemini_client():
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT

    key = Config.GEMINI_API_KEY
    if key and not key.startswith("your_") and genai:
        try:
            _GEMINI_CLIENT = genai.Client(api_key=key)
        except Exception as e:
            print(f"[RAGService] Gemini client initialization error: {e}")
    return _GEMINI_CLIENT


def _hash_text_fallback_embedding(text: str, dim: int = 768) -> List[float]:
    """Deterministic, vocabulary-aware fallback pseudo-embedding for offline/test mode."""
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    if not words:
        return vec.tolist()

    for idx, word in enumerate(words):
        # Hash word into vector space
        h = hash(word) % dim
        weight = 1.0 / (1.0 + (idx * 0.05))
        vec[h] += weight
        vec[(h * 31) % dim] += weight * 0.5

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def embed_text(text: str) -> List[float]:
    """Generates a 768-dimensional vector embedding for text using Gemini or deterministic fallback."""
    text = (text or "").strip()
    if not text:
        return [0.0] * 768

    client = get_gemini_client()
    if client:
        try:
            # Call Gemini text-embedding-004
            response = client.models.embed_content(
                model=Config.EMBEDDING_MODEL,
                contents=text,
            )
            if hasattr(response, "embedding") and response.embedding:
                return response.embedding.values
            if hasattr(response, "embeddings") and response.embeddings:
                return response.embeddings[0].values
        except Exception as e:
            print(f"[RAGService] Gemini embedding call failed: {e}. Using deterministic fallback.")

    return _hash_text_fallback_embedding(text)


def _load_and_index_collection(collection_name: str) -> List[Dict[str, Any]]:
    """Loads a seed knowledge collection JSON and pre-computes embeddings."""
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
        except Exception as e:
            print(f"[RAGService] Error reading seed collection {collection_name}: {e}")

    # Build searchable text representation for each document
    vectors = []
    for item in items:
        if collection_name == "kb_interview_questions":
            search_str = f"{item.get('question_text', '')} Role: {item.get('role', '')} Skill: {item.get('skill', '')} Stage: {item.get('stage', '')}"
        elif collection_name == "kb_skills_taxonomy":
            syns = ", ".join(item.get("synonyms", []))
            adjs = ", ".join(item.get("adjacent_skills", {}).keys())
            search_str = f"{item.get('canonical_skill', '')} Category: {item.get('category', '')} Synonyms: {syns} Related: {adjs} Description: {item.get('description', '')}"
        elif collection_name == "kb_jd_corpus":
            reqs = ", ".join(item.get("required_skills", []))
            search_str = f"{item.get('role_title', '')} Domain: {item.get('domain', '')} Skills: {reqs} Content: {item.get('raw_text', '')}"
        elif collection_name == "kb_resume_best_practices":
            search_str = f"{item.get('category', '')} Tags: {', '.join(item.get('domain_tags', []))} Rule: {item.get('rule_description', '')} Before: {item.get('before_example', '')} After: {item.get('after_example', '')}"
        elif collection_name == "kb_company_interview_style":
            principles = ", ".join(item.get("culture_principles", []))
            search_str = f"{item.get('company_name', '')} Principles: {principles} Focus: {item.get('evaluation_focus', '')}"
        else:
            search_str = json.dumps(item)

        item["_search_text"] = search_str
        vec = embed_text(search_str)
        item["_embedding"] = vec
        vectors.append(vec)

    _COLLECTION_CACHE[collection_name] = items
    if vectors:
        _EMBEDDINGS_CACHE[collection_name] = np.array(vectors, dtype=np.float32)
    else:
        _EMBEDDINGS_CACHE[collection_name] = np.empty((0, 768), dtype=np.float32)

    return items


def retrieve(
    query: Union[str, List[float]],
    collection: str,
    top_k: int = 5,
    filter_criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Shared RAG retrieval utility used by ALL specialist agents.
    Searches the specified knowledge collection using pgvector or local cosine similarity.
    
    Returns structured results:
    [
        {
            "id": "...",
            "item": {...},
            "similarity": 0.89,
            "collection": collection
        }
    ]
    """
    filter_criteria = filter_criteria or {}

    # Convert query text to embedding if necessary
    if isinstance(query, str):
        query_text = query
        query_vec = np.array(embed_text(query_text), dtype=np.float32)
    else:
        query_text = "raw_vector_query"
        query_vec = np.array(query, dtype=np.float32)

    # 1. Try remote Supabase pgvector RPC function if configured
    if supabase_service.supabase:
        try:
            rpc_name = f"match_{collection.replace('kb_', '')}"
            params = {
                "query_embedding": query_vec.tolist(),
                "match_count": top_k,
                "match_threshold": 0.1
            }
            # Add specific filters if applicable
            if "role" in filter_criteria:
                params["filter_role"] = filter_criteria["role"]
            if "stage" in filter_criteria:
                params["filter_stage"] = filter_criteria["stage"]
            if "domain" in filter_criteria:
                params["filter_domain"] = filter_criteria["domain"]
            if "category" in filter_criteria:
                params["filter_category"] = filter_criteria["category"]
            if "company" in filter_criteria:
                params["filter_company"] = filter_criteria["company"]

            res = supabase_service.supabase.rpc(rpc_name, params).execute()
            if res.data:
                results = []
                for row in res.data:
                    sim = float(row.get("similarity", 0.0))
                    results.append({
                        "id": str(row.get("id", "")),
                        "item": row,
                        "similarity": round(sim, 4),
                        "collection": collection
                    })
                return results
        except Exception as e:
            print(f"[RAGService] Supabase RPC {collection} failed: {e}. Using local in-memory vector index.")

    # 2. Local in-memory cosine similarity retrieval
    items = _load_and_index_collection(collection)
    if not items:
        return []

    matrix = _EMBEDDINGS_CACHE.get(collection)
    if matrix is None or len(matrix) == 0:
        return []

    # Compute cosine similarities: dot(A, B) / (norm(A) * norm(B))
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        query_norm = 1.0

    matrix_norms = np.linalg.norm(matrix, axis=1)
    matrix_norms[matrix_norms == 0] = 1.0

    scores = np.dot(matrix, query_vec) / (matrix_norms * query_norm)

    # Filter items based on filter_criteria
    scored_candidates = []
    for idx, (item, score) in enumerate(zip(items, scores)):
        # Apply filters
        match = True
        for k, v in filter_criteria.items():
            if not v:
                continue
            item_val = item.get(k)
            if isinstance(item_val, str):
                if v.lower() not in item_val.lower():
                    match = False
                    break
            elif isinstance(item_val, list):
                if not any(v.lower() in str(x).lower() for x in item_val):
                    match = False
                    break

        if match:
            clean_item = {k: v for k, v in item.items() if not k.startswith("_")}
            item_id = clean_item.get("id") or clean_item.get("canonical_skill") or f"{collection}-{idx}"
            scored_candidates.append({
                "id": str(item_id),
                "item": clean_item,
                "similarity": round(float(score), 4),
                "collection": collection
            })

    # Sort descending by similarity
    scored_candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return scored_candidates[:top_k]


# Pre-warm collections on module import
for col in [
    "kb_interview_questions",
    "kb_skills_taxonomy",
    "kb_jd_corpus",
    "kb_resume_best_practices",
    "kb_company_interview_style",
]:
    _load_and_index_collection(col)
