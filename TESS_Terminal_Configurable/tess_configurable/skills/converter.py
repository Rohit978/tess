"""
Converter Skill - Convert between file formats.
"""

import os
from pathlib import Path
from typing import Union, List, Optional


class ConverterSkill:
    """
    Converts files between formats (images to PDF, etc.).
    """
    
    def run(self, sub_action: str, source_paths: Union[str, List[str]], 
            output_filename: Optional[str] = None) -> str:
        """
        Run conversion.
        
        Args:
            sub_action: Conversion type
            source_paths: Input file(s)
            output_filename: Output file name
            
        Returns:
            Status message
        """
        if isinstance(source_paths, str):
            source_paths = [source_paths]
        
        if sub_action in ["images_to_pdf", "image_to_pdf"]:
            return self._images_to_pdf(source_paths, output_filename)
        elif sub_action == "docx_to_pdf":
            return self._docx_to_pdf(source_paths[0], output_filename)
        else:
            return f"Unknown conversion: {sub_action}"
    
    def _images_to_pdf(self, image_paths: List[str], output: Optional[str]) -> str:
        """Convert images to PDF."""
        try:
            from PIL import Image
            
            # Validate input paths
            valid_paths = []
            for path in image_paths:
                path = os.path.expanduser(path.strip('"\''))  # Remove quotes
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    return f"Image not found: {path}"
            
            if not valid_paths:
                return "No valid images found. Check the file paths."
            
            # Set output path
            if not output:
                # Use first image name as base
                base = os.path.splitext(valid_paths[0])[0]
                output = f"{base}.pdf"
            
            output = os.path.expanduser(output.strip('"\''))
            
            if not output.endswith('.pdf'):
                output += '.pdf'
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output) or '.'
            os.makedirs(output_dir, exist_ok=True)
            
            # Open and convert images
            images = []
            for path in valid_paths:
                try:
                    img = Image.open(path)
                    # Convert to RGB if necessary (handles RGBA, P mode, etc.)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # Create white background for transparency
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                            img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append(img)
                except Exception as e:
                    return f"Error opening image {path}: {e}"
            
            if not images:
                return "No valid images could be processed"
            
            # Save as PDF
            first = images[0]
            rest = images[1:] if len(images) > 1 else []
            
            first.save(
                output, 
                "PDF", 
                resolution=100.0, 
                save_all=True, 
                append_images=rest
            )
            
            # Close images to free memory
            for img in images:
                img.close()
            
            # Return absolute path for clarity
            abs_path = os.path.abspath(output)
            return f"✓ Created PDF: {abs_path} ({len(images)} page{'s' if len(images) > 1 else ''})"
            
        except ImportError:
            return "PIL not installed. Run: pip install pillow"
        except Exception as e:
            return f"Conversion error: {e}"
    
    def _docx_to_pdf(self, docx_path: str, output: Optional[str]) -> str:
        """Convert DOCX to PDF."""
        try:
            from docx2pdf import convert
            
            if not output:
                output = docx_path.replace('.docx', '.pdf')
            
            convert(docx_path, output)
            return f"Converted: {output}"
            
        except ImportError:
            return "docx2pdf not installed. Run: pip install docx2pdf"
        except Exception as e:
            return f"Conversion error: {e}"
