import fitz
import os

pdf_path = r"c:\Users\01roh\OneDrive\Desktop\Side_Projectss\IDE\TESS_Desktop\TESS_Terminal_Pro\Narendra_Modi_Biography.pdf"

if not os.path.exists(pdf_path):
    print(f"Error: File not found at {pdf_path}")
    exit(1)

try:
    doc = fitz.open(pdf_path)
    print(f"Success! Opened PDF. Pages: {len(doc)}")
    
    # Try reading first page
    if len(doc) > 0:
        text = doc[0].get_text()
        print(f"First Page Preview:\n{text[:200]}...")
    
    doc.close()
except Exception as e:
    print(f"Error reading PDF: {e}")
