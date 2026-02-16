import os
import fitz # PyMuPDF
from ..core.logger import setup_logger

logger = setup_logger("PDFSkill")

class PDFSkill:
    """
    Advanced PDF Editing Skill.
    Supports:
    - Merging multiple PDFs
    - Splitting a PDF into pages
    - Extracting text from a PDF
    - Replacing text (experimental)
    """
    def __init__(self):
        pass

    def run(self, action_type, source, output_name=None, extras=None):
        """
        Executes the PDF operation based on the action_type.
        """
        try:
            if action_type == "merge":
                return self.merge(source, output_name)
            elif action_type == "split":
                return self.split(source, extras.get("pages"), output_name)
            elif action_type == "extract_text":
                return self.extract_text(source)
            elif action_type == "replace_text":
                return self.replace_text(source, extras.get("search"), extras.get("replace"), output_name)
            else:
                return f"Unknown PDF operation: {action_type}"
        except Exception as e:
            logger.error(f"PDF operation failed: {e}")
            return f"PDF operation failed: {e}"

    def merge(self, source_paths, output_name):
        """Merges multiple PDF files into one."""
        if isinstance(source_paths, str):
            source_paths = [p.strip() for p in source_paths.split(",")]

        valid_paths = [p for p in source_paths if os.path.exists(p)]
        if not valid_paths:
            return "Error: No valid PDF files found for merging."

        if not output_name:
            output_name = "merged_document.pdf"

        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"

        output_path = os.path.join(os.path.dirname(valid_paths[0]), output_name)
        
        doc_out = fitz.open()
        for path in valid_paths:
            try:
                doc_in = fitz.open(path)
                doc_out.insert_pdf(doc_in)
                doc_in.close()
            except Exception as e:
                logger.warning(f"Skipping {path}: {e}")

        doc_out.save(output_path)
        doc_out.close()
        return f"Successfully merged {len(valid_paths)} files into: {output_path}"

    def split(self, source_path, pages, output_name):
        """Splits specific pages from a PDF into a new file."""
        if not os.path.exists(source_path):
            return f"Error: File not found: {source_path}"

        if not pages:
            return "Error: No pages specified for splitting (e.g., '1,2,5' or '1-5')."

        if not output_name:
            base = os.path.splitext(os.path.basename(source_path))[0]
            output_name = f"{base}_split.pdf"

        output_path = os.path.join(os.path.dirname(source_path), output_name)
        
        doc_in = fitz.open(source_path)
        doc_out = fitz.open()

        # Parse page strings (1-indexed for users, 0-indexed for fitz)
        try:
            if "-" in str(pages):
                start, end = map(int, pages.split("-"))
                doc_out.insert_pdf(doc_in, from_page=start-1, to_page=end-1)
            else:
                p_list = [int(p.strip()) - 1 for p in str(pages).split(",")]
                for p in p_list:
                    if 0 <= p < len(doc_in):
                        doc_out.insert_pdf(doc_in, from_page=p, to_page=p)
        except Exception as e:
            return f"Error parsing pages '{pages}': {e}"

        doc_out.save(output_path)
        doc_in.close()
        doc_out.close()
        return f"Successfully split pages {pages} into: {output_path}"

    def extract_text(self, source_path):
        """Extracts all text from a PDF."""
        if not os.path.exists(source_path):
            return f"Error: File not found: {source_path}"

        doc = fitz.open(source_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        if not text.strip():
            return "No text could be extracted (the PDF might be image-based/scanned)."
        return text

    def replace_text(self, source_path, search_text, replace_text, output_name):
        """[EXPERIMENTAL] Redacts search_text and overlays replace_text."""
        if not os.path.exists(source_path):
            return f"Error: File not found: {source_path}"

        if not search_text or not replace_text:
            return "Error: Missing search or replacement text."

        if not output_name:
            base = os.path.splitext(os.path.basename(source_path))[0]
            output_name = f"{base}_edited.pdf"

        output_path = os.path.join(os.path.dirname(source_path), output_name)
        
        doc = fitz.open(source_path)
        count = 0
        
        for page in doc:
            areas = page.search_for(search_text)
            for rect in areas:
                # 1. Redact original (optional, prevents overlap mess)
                page.add_redact_annot(rect, fill=(1,1,1)) # White fill
                page.apply_redactions()
                
                # 2. Overlay new text
                # Note: This is basic and doesn't match original font perfectly
                page.insert_text(rect.bl - (0, 2), replace_text, fontsize=11, color=(0,0,0))
                count += 1

        doc.save(output_path)
        doc.close()
        return f"Successfully replaced '{search_text}' with '{replace_text}' in {count} locations. Saved to: {output_path}"
