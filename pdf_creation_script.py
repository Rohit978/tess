from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
pdf.set_font('DejaVu', '', 12)

with open('modi_bio.txt', 'r', encoding='utf-8') as f:
    text = f.read()

pdf.multi_cell(0, 5, text)

pdf.output("modi_bio.pdf")