"""
Document text extraction service — delegates to the AI service.

The AI service (cixio-hub/ai, port 8003) handles:
  - PDF extraction via PyMuPDF
  - DOCX extraction via python-docx
  - Plain text reading
  - Image OCR via Tesseract

Students (AI/LLM role): implement extraction in cixio-hub/ai/app/rag/document_extractor.py
Students (Backend role): this file is already wired.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.config import settings
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)


async def extract_text(file_path: str, file_type: str) -> str:
    """
    Extract plain text from a file.

    Supports two path types:
      - HTTP(S) URLs: fetches file bytes over the network.
      - Local paths: reads from the filesystem (absolute or relative).

    Parses PDF via PyMuPDF, plain text/markdown via UTF-8 decode.
    """
    ft = file_type.lower().strip()
    content_bytes: bytes | None = None

    logger.info("Extracting text: file_path=%s, file_type=%s", file_path, file_type)

    # 1. Retrieve file content
    if file_path.startswith("http://") or file_path.startswith("https://"):
        try:
            client = get_http_client()
            try:
                resp = await client.get(file_path)
                resp.raise_for_status()
                content_bytes = resp.content
            except Exception as first_exc:
                alt_url = None
                if "host.docker.internal" in file_path:
                    alt_url = file_path.replace("host.docker.internal", "localhost")
                elif "localhost" in file_path:
                    alt_url = file_path.replace("localhost", "host.docker.internal")
                if alt_url:
                    resp = await client.get(alt_url)
                    resp.raise_for_status()
                    content_bytes = resp.content
                else:
                    raise first_exc
            logger.info("Fetched %d bytes from %s", len(content_bytes), file_path)
        except Exception as exc:
            logger.error("Failed to fetch file over HTTP: %s", exc)
    else:
        p = Path(file_path)
        if p.exists() and p.is_file():
            content_bytes = p.read_bytes()
            logger.info("Read %d bytes from %s", len(content_bytes), p)
        else:
            clean = file_path
            if "uploads/" in clean:
                clean = clean.split("uploads/", 1)[1]
            rel_p = Path("uploads") / clean.lstrip("/")
            if rel_p.exists() and rel_p.is_file():
                content_bytes = rel_p.read_bytes()
                logger.info("Read %d bytes from relative path %s", len(content_bytes), rel_p)
            else:
                logger.error("File not found: %s", file_path)

    # 2. Parse content
    if content_bytes is not None:
        if "txt" in ft or "md" in ft or "text" in ft:
            return content_bytes.decode("utf-8", errors="ignore")
        elif "pdf" in ft:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=content_bytes, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                return text
            except Exception as exc:
                logger.error("PDF extraction failed: %s", exc)

    logger.warning("Extraction failed for %s (type %s). Returning empty.", file_path, file_type)
    return ""

