import os
import fitz
from tess_cli.skills.pdf_skill import PDFSkill

def test_pdf_skill():
    skill = PDFSkill()
    test_dir = "pdf_test"
    os.makedirs(test_dir, exist_ok=True)
    
    file1 = os.path.join(test_dir, "test1.pdf")
    file2 = os.path.join(test_dir, "test2.pdf")
    merged = "merged.pdf"
    
    # 1. Create two simple PDFs
    doc1 = fitz.open()
    page1 = doc1.new_page()
    page1.insert_text((50, 50), "This is PDF Number One.")
    doc1.save(file1)
    doc1.close()
    
    doc2 = fitz.open()
    page2 = doc2.new_page()
    page2.insert_text((50, 50), "This is PDF Number Two.")
    doc2.save(file2)
    doc2.close()
    
    print(f"Created test files: {file1}, {file2}")
    
    # 2. Test Merge
    print("\nTesting Merge...")
    merge_res = skill.run("merge", f"{file1}, {file2}", merged)
    print(merge_res)
    
    merged_path = os.path.join(test_dir, merged)
    if os.path.exists(merged_path):
        print(f"Verification: {merged_path} exists.")
    else:
        print(f"Verification FAILED: {merged_path} NOT found.")
        return

    # 3. Test Text Extraction
    print("\nTesting Text Extraction...")
    extract_res = skill.run("extract_text", merged_path)
    print("Extracted Text Preview:")
    print(f"---{extract_res[:100]}---")
    
    if "Number One" in extract_res and "Number Two" in extract_res:
        print("Verification: Text extraction successful.")
    else:
        print("Verification FAILED: Extracted text missing content.")
        
    print("\nPDF Verification Complete!")

if __name__ == "__main__":
    test_pdf_skill()
