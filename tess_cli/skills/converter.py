import os
import img2pdf
from docx2pdf import convert
from ..core.logger import setup_logger

logger = setup_logger("FileConverter")

class FileConverter:
    """Converts files (Images -> PDF, DOCX -> PDF)."""
    
    def images_to_pdf(self, source_paths, output_name=None):
        if isinstance(source_paths, str): source_paths = [source_paths]
            
        valid = [p for p in source_paths if os.path.exists(p)]
        if not valid: return "No valid images."
            
        if not output_name:
            output_name = f"{os.path.splitext(os.path.basename(valid[0]))[0]}_converted.pdf"
            
        if not output_name.lower().endswith(".pdf"): output_name += ".pdf"
            
        out_path = os.path.join(os.path.dirname(valid[0]), output_name)
        logger.info(f"Converting {len(valid)} images -> {out_path}")
        
        try:
            with open(out_path, "wb") as f:
                f.write(img2pdf.convert(valid))
            return f"Created PDF: {out_path}"
        except Exception as e:
            return f"Conversion error: {e}"

    def docx_to_pdf(self, source_path, output_name=None):
        if isinstance(source_path, list): source_path = source_path[0] if source_path else None
        if not source_path or not os.path.exists(source_path): return "File not found."
            
        if not output_name:
            output_name = f"{os.path.splitext(os.path.basename(source_path))[0]}.pdf"
            
        out_path = os.path.join(os.path.dirname(source_path), output_name)
        logger.info(f"DOCX -> PDF: {out_path}")
        
        try:
            convert(source_path, out_path)
            return f"Converted: {out_path}"
        except Exception as e:
            return f"Error: {e}"
