from pathlib import Path

from fpdf import FPDF


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "tess_architecture_analysis.md"
OUTPUT = ROOT / "docs" / "tess_architecture_analysis.pdf"


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "TESS Architecture and Logic Analysis", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(90, 90, 90)
        self.cell(0, 6, "Generated from repository analysis", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def sanitize_text(text: str) -> str:
    replacements = {
        "\u2229": " intersect ",
        "\u222a": " union ",
        "\u2013": "-",
        "\u2014": "-",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2192": "->",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


def render_markdown(pdf: ReportPDF, text: str) -> None:
    for raw_line in text.splitlines():
        line = sanitize_text(raw_line.rstrip())

        if not line:
            pdf.ln(3)
            continue

        if line.startswith("## "):
            pdf.ln(2)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 8, line[3:])
            pdf.ln(1)
            continue

        if line.startswith("### "):
            pdf.ln(1)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 7, line[4:])
            continue

        if line.startswith("- "):
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, f"- {line[2:]}")
            continue

        if line[:2].isdigit() and line[1:3] == ". ":
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, line)
            continue

        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, line)


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    render_markdown(pdf, text)
    pdf.output(str(OUTPUT))

    print(str(OUTPUT))


if __name__ == "__main__":
    main()
