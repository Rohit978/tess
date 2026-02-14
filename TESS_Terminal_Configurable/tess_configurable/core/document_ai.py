"""
Document AI - PDF, image OCR, and document understanding.
"""

import os
import io
from pathlib import Path
from typing import Optional, List, Dict, Union


class DocumentAI:
    """
    Intelligent document processing:
    - PDF text extraction and summarization
    - Image OCR (Optical Character Recognition)
    - Document analysis and insights
    """
    
    def __init__(self, brain=None):
        self.brain = brain
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            import PyPDF2
            
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            return text if text else "No text found in PDF"
            
        except ImportError:
            return "PyPDF2 not installed. Run: pip install PyPDF2"
        except Exception as e:
            return f"PDF extraction error: {e}"
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text
        """
        try:
            import pytesseract
            from PIL import Image
            
            # Open image
            image = Image.open(image_path)
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            return text if text.strip() else "No text found in image"
            
        except ImportError:
            return "Tesseract not installed. Run: pip install pytesseract pillow"
        except Exception as e:
            return f"OCR error: {e}"
    
    def extract_text_from_docx(self, docx_path: str) -> str:
        """
        Extract text from Word document.
        
        Args:
            docx_path: Path to .docx file
            
        Returns:
            Extracted text
        """
        try:
            from docx import Document
            
            doc = Document(docx_path)
            text = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text)
            
            return "\n".join(text) if text else "No text found in document"
            
        except ImportError:
            return "python-docx not installed. Run: pip install python-docx"
        except Exception as e:
            return f"DOCX extraction error: {e}"
    
    def summarize_document(self, file_path: str, max_length: int = 500) -> str:
        """
        Extract and summarize document content.
        
        Args:
            file_path: Path to document
            max_length: Maximum summary length
            
        Returns:
            Summary of document
        """
        # Extract text based on file type
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            text = self.extract_text_from_docx(file_path)
        elif ext in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        else:
            return f"Unsupported file type: {ext}"
        
        if text.startswith("Error") or text.startswith("No text"):
            return text
        
        # Truncate if too long
        if len(text) > 10000:
            text = text[:10000] + "... [truncated]"
        
        # Use AI to summarize if brain available
        if self.brain and len(text) > 500:
            try:
                prompt = f"""Summarize this document in {max_length} characters or less:

{text[:3000]}

Summary:"""
                
                messages = [{"role": "user", "content": prompt}]
                summary = self.brain.request_completion(messages, max_tokens=300, json_mode=False)
                return summary or text[:max_length]
            except:
                pass
        
        # Fallback: return first part
        return text[:max_length] + "..." if len(text) > max_length else text
    
    def analyze_image(self, image_path: str) -> str:
        """
        Analyze image content (describe what's in it).
        
        Args:
            image_path: Path to image
            
        Returns:
            Description of image content
        """
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            
            # Basic image info
            info = {
                "format": img.format,
                "size": img.size,
                "mode": img.mode,
                "file_size": f"{os.path.getsize(image_path) / 1024:.1f} KB"
            }
            
            # Try OCR
            ocr_text = self.extract_text_from_image(image_path)
            has_text = not ocr_text.startswith("No text") and not ocr_text.startswith("Tesseract")
            
            result = f"Image: {info['format']} {info['size'][0]}x{info['size'][1]} ({info['file_size']})"
            
            if has_text:
                result += f"\n\nText found:\n{ocr_text[:500]}"
            
            return result
            
        except Exception as e:
            return f"Image analysis error: {e}"
    
    def batch_process(self, folder_path: str, file_types: List[str] = None) -> Dict[str, str]:
        """
        Process all documents in a folder.
        
        Args:
            folder_path: Folder to process
            file_types: List of extensions to process (default: pdf, docx, txt)
            
        Returns:
            Dictionary of filename -> extracted content
        """
        if file_types is None:
            file_types = ['.pdf', '.docx', '.txt', '.md']
        
        results = {}
        folder = Path(folder_path)
        
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in file_types:
                try:
                    ext = file_path.suffix.lower()
                    
                    if ext == '.pdf':
                        content = self.extract_text_from_pdf(str(file_path))
                    elif ext == '.docx':
                        content = self.extract_text_from_docx(str(file_path))
                    else:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    
                    results[file_path.name] = content[:1000]  # Limit storage
                    
                except Exception as e:
                    results[file_path.name] = f"Error: {e}"
        
        return results
    
    def search_in_documents(self, folder_path: str, query: str) -> List[Dict]:
        """
        Search for text across multiple documents.
        
        Args:
            folder_path: Folder containing documents
            query: Search query
            
        Returns:
            List of matches with context
        """
        results = []
        documents = self.batch_process(folder_path)
        
        query_lower = query.lower()
        
        for filename, content in documents.items():
            if query_lower in content.lower():
                # Find context around match
                idx = content.lower().find(query_lower)
                start = max(0, idx - 100)
                end = min(len(content), idx + len(query) + 100)
                context = content[start:end]
                
                results.append({
                    "file": filename,
                    "context": context,
                    "position": idx
                })
        
        return results
