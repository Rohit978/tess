import sys
import os

try:
    from fpdf import FPDF
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"])
    from fpdf import FPDF

def clean_text(text):
    return "".join(c for c in text if ord(c) < 128)

def create_pdf(input_md, output_pdf):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    
    if not os.path.exists(input_md):
        print(f"Error: {input_md} not found.")
        return

    with open(input_md, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue
        
        line = clean_text(line)
        
        if line.startswith('# '):
            pdf.set_font("helvetica", "B", 16)
            pdf.write(5, line[2:])
            pdf.ln(10)
        elif line.startswith('## '):
            pdf.set_font("helvetica", "B", 14)
            pdf.write(5, line[3:])
            pdf.ln(8)
        else:
            pdf.set_font("helvetica", size=11)
            pdf.write(5, line)
            pdf.ln(6)

    pdf.output(output_pdf)
    print(f"PDF generated successfully: {output_pdf}")

if __name__ == "__main__":
    create_pdf('modi_report_content.md', 'Narendra_Modi_Biography.pdf')
