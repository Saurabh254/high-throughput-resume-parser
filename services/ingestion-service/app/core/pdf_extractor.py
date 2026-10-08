import fitz  # PyMuPDF
import re
import hashlib
from typing import Dict, Any, Tuple

class PDFExtractor:
    @staticmethod
    def extract_from_bytes(pdf_bytes: bytes, filename: str = "resume.pdf") -> Tuple[str, Dict[str, Any]]:
        """
        Extracts clean text and structural metadata from PDF bytes.
        Fast in-memory operation (no disk writing).
        """
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        pages_text = []
        metadata = {
            "filename": filename,
            "file_hash": file_hash,
            "page_count": len(doc),
            "author": doc.metadata.get("author", ""),
            "title": doc.metadata.get("title", ""),
            "creator": doc.metadata.get("creator", ""),
        }
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text:
                pages_text.append(text)
                
        doc.close()
        
        raw_text = "\n".join(pages_text)
        cleaned_text = PDFExtractor.clean_extracted_text(raw_text)
        
        return cleaned_text, metadata

    @staticmethod
    def clean_extracted_text(text: str) -> str:
        """
        Cleans OCR/PDF artifacts, fixes broken hyphenations, normalizes whitespace.
        """
        if not text:
            return ""
            
        # Fix line-broken hyphens: e.g. "micro-\nservices" -> "microservices"
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # Replace non-breaking spaces and irregular unicode whitespaces
        text = text.replace('\xa0', ' ').replace('\u200b', '')
        
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Replace 3 or more consecutive newlines with 2 newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
