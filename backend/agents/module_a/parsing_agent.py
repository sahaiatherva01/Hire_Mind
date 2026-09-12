"""
HireMind AI — Parsing Agent (Module A)
Extracts raw text and analyzes document layout from PDF / DOCX bytes.
"""
import io
import docx
import fitz  # PyMuPDF
from typing import Dict, Any
from agents.base_agent import BaseAgent


class ParsingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="ParsingAgent",
            orchestrator_name="module_a_orchestrator"
        )

    def parse_document(self, file_bytes: bytes, filename: str, entity_id: str = None) -> Dict[str, Any]:
        """
        Parses document text, counts pages, and detects multi-column layout risks.
        """
        fn_lower = filename.lower()
        if fn_lower.endswith(".pdf"):
            metadata = self._parse_pdf(file_bytes)
        elif fn_lower.endswith((".docx", ".doc")):
            metadata = self._parse_docx(file_bytes)
        else:
            # Fallback treat as plain text
            text = file_bytes.decode("utf-8", errors="ignore")
            metadata = {
                "raw_text": text,
                "page_count": 1,
                "is_multi_column": False,
                "has_tables": False,
                "extraction_method": "plain_text"
            }

        raw_text = metadata.get("raw_text", "").strip()
        confidence = 0.98 if len(raw_text) > 100 else 0.40

        citations = [
            f"Document length: {len(raw_text)} characters",
            f"Page count: {metadata.get('page_count')}",
            f"Layout multi-column detected: {metadata.get('is_multi_column')}"
        ]

        return self.build_agent_output(
            result=metadata,
            citations=citations,
            reasoning=f"Successfully extracted {len(raw_text)} characters across {metadata.get('page_count')} pages using PyMuPDF/docx parser.",
            confidence=confidence,
            entity_id=entity_id,
            entity_type="resume_parse"
        )

    def _parse_pdf(self, file_bytes: bytes) -> Dict[str, Any]:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text = []
        is_multi_column = False
        has_tables = False

        for page in doc:
            text = page.get_text()
            pages_text.append(text)

            # Analyze text block coordinates to check for 2-column sidebar layouts
            blocks = page.get_text("blocks")
            left_cols = 0
            right_cols = 0
            page_width = page.rect.width

            for b in blocks:
                x0, y0, x1, y1, b_text, block_no, block_type = b
                if block_type == 0:  # text block
                    if x1 < (page_width * 0.48):
                        left_cols += 1
                    elif x0 > (page_width * 0.52):
                        right_cols += 1

            if left_cols >= 3 and right_cols >= 3:
                is_multi_column = True

            # Table detection heuristic
            tabs = page.find_tables()
            if tabs and tabs.tables:
                has_tables = True

        combined_text = "\n".join(pages_text)
        return {
            "raw_text": combined_text,
            "page_count": len(doc),
            "is_multi_column": is_multi_column,
            "has_tables": has_tables,
            "extraction_method": "pymupdf_fitz"
        }

    def _parse_docx(self, file_bytes: bytes) -> Dict[str, Any]:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        has_tables = len(doc.tables) > 0

        # Extract text from tables if present
        table_texts = []
        for t in doc.tables:
            for row in t.rows:
                row_str = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if row_str:
                    table_texts.append(row_str)

        all_text = "\n".join(paragraphs + table_texts)
        return {
            "raw_text": all_text,
            "page_count": max(1, len(all_text) // 2500),
            "is_multi_column": False,
            "has_tables": has_tables,
            "extraction_method": "python_docx"
        }
