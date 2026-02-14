import os
import img2pdf
from PIL import Image
from docx2pdf import convert
from ..core.logger import setup_logger

logger = setup_logger("ConverterSkill")

class ConverterSkill:
    """
    Skill for File Conversion.
    Supports:
    - Images (JPG, PNG) -> PDF
    - DOCX -> PDF
    """
    def __init__(self):
        pass

    def run(self, action_type, source, output_name=None):
        """
        Executes the conversion.
        """
        try:
            if action_type in ["images_to_pdf", "image_to_pdf"]:
                return self._images_to_pdf(source, output_name)
            elif action_type == "docx_to_pdf":
                return self._docx_to_pdf(source, output_name)
            else:
                return f"Unknown conversion type: {action_type}"
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return f"Conversion failed: {e}"

    def _images_to_pdf(self, source_paths, output_name):
        # Handle single path string
        if isinstance(source_paths, str):
            source_paths = [source_paths]
            
        # Validate paths
        valid_paths = [p for p in source_paths if os.path.exists(p)]
        if not valid_paths:
            return "No valid image files found."
            
        # Determine output filename
        if not output_name:
            # Default to name of first image
            base = os.path.splitext(os.path.basename(valid_paths[0]))[0]
            output_name = f"{base}_converted.pdf"
            
        # Ensure output ends in .pdf
        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"
            
        # Save in same dir as first image
        output_dir = os.path.dirname(valid_paths[0])
        output_path = os.path.join(output_dir, output_name)
        
        logger.info(f"Converting {len(valid_paths)} images to {output_path}...")
        
        try:
            # Convert images to PDF bytes
            # img2pdf.convert() expects bytes or file objects, not just paths sometimes
            # Safer to open them
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(valid_paths))
            return f"Successfully created PDF: {output_path}"
        except Exception as e:
            return f"Error converting images: {e}"

    def _docx_to_pdf(self, source_path, output_name):
        # Handle list input (LLM might pass a list even for single file)
        if isinstance(source_path, list):
            if not source_path:
                return "No source file provided."
            source_path = source_path[0]
            
        if not os.path.exists(source_path):
            return f"File not found: {source_path}"
            
        if not output_name:
            base = os.path.splitext(os.path.basename(source_path))[0]
            output_name = f"{base}.pdf"
            
        output_dir = os.path.dirname(source_path)
        output_path = os.path.join(output_dir, output_name)
        
        logger.info(f"Converting DOCX: {source_path} -> {output_path}")
        
        try:
            # docx2pdf handles conversion
            convert(source_path, output_path)
            return f"Successfully converted to PDF: {output_path}"
        except Exception as e:
            return f"Error converting DOCX: {e}"
