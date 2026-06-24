#!/usr/bin/env python3
"""Generate TESTING_GUIDE.pdf from TESTING_GUIDE.md using fpdf2."""

import re
from pathlib import Path
from fpdf import FPDF
from fpdf.enums import XPos, YPos

MD_PATH = Path(__file__).parent / "TESTING_GUIDE.md"
PDF_PATH = Path(__file__).parent / "TESTING_GUIDE.pdf"

PAGE_W = 210
MARGIN = 18
TEXT_W = PAGE_W - 2 * MARGIN
CODE_BG = (245, 245, 245)
TABLE_HDR = (30, 80, 150)
TABLE_ALT = (235, 241, 250)
WHITE = (255, 255, 255)
BLACK = (30, 30, 30)
BLUE = (30, 80, 150)


def ascii_safe(text):
    """Normalise text to latin-1 safe ASCII equivalents."""
    text = text.replace("—", "--")   # em dash
    text = text.replace("–", "-")    # en dash
    text = text.replace("‘", "'")    # left single quote
    text = text.replace("’", "'")    # right single quote
    text = text.replace("“", '"')    # left double quote
    text = text.replace("”", '"')    # right double quote
    text = text.replace("×", "x")   # multiplication sign
    text = text.replace("≥", ">=")  # >=
    text = text.replace("≤", "<=")  # <=
    text = text.replace("≠", "!=")  # !=
    text = text.replace("±", "+/-") # plus-minus
    text = text.replace("→", "->")  # right arrow
    text = text.replace("←", "<-")  # left arrow
    text = text.replace("•", "-")   # bullet
    text = text.replace("·", ".")   # middle dot
    text = text.replace(" ", " ")   # non-breaking space
    text = text.replace("…", "...") # ellipsis
    # Replace remaining non-latin-1 safely
    return text.encode("latin-1", errors="replace").decode("latin-1")


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=MARGIN)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, "Gen-Health Analytics -- Test Data & Testing Guide", align="L")
        self.cell(0, 6, "Page " + str(self.page_no()), align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, "Gen-Health Analytics -- preventive health informatics capstone", align="C")


def render_code(pdf, lines):
    pdf.set_fill_color(*CODE_BG)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_font("Courier", size=8)
    pdf.set_text_color(*BLACK)
    line_h = 5
    block_h = len(lines) * line_h + 4
    y = pdf.get_y()
    if y + block_h > pdf.h - MARGIN:
        pdf.add_page()
        y = pdf.get_y()
    pdf.rect(MARGIN, y, TEXT_W, block_h, style="F")
    pdf.set_xy(MARGIN + 2, y + 2)
    for line in lines:
        pdf.set_x(MARGIN + 2)
        pdf.cell(TEXT_W - 4, line_h, ascii_safe(line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)


def render_table(pdf, rows):
    if not rows:
        return
    col_count = len(rows[0])
    col_w = TEXT_W / col_count
    line_h = 6

    for i, row in enumerate(rows):
        if i == 0:
            pdf.set_fill_color(*TABLE_HDR)
            pdf.set_text_color(*WHITE)
            pdf.set_font("Helvetica", "B", 8)
        elif i % 2 == 0:
            pdf.set_fill_color(*TABLE_ALT)
            pdf.set_text_color(*BLACK)
            pdf.set_font("Helvetica", size=8)
        else:
            pdf.set_fill_color(*WHITE)
            pdf.set_text_color(*BLACK)
            pdf.set_font("Helvetica", size=8)

        # Estimate max lines in this row for row height
        max_lines = 1
        for cell in row:
            pdf.set_font("Helvetica", size=8)
            words = ascii_safe(cell).split()
            line = ""
            count = 0
            for w in words:
                test = (line + " " + w).strip()
                if pdf.get_string_width(test) < col_w - 4:
                    line = test
                else:
                    count += 1
                    line = w
            max_lines = max(max_lines, count + 1)

        row_h = max_lines * line_h

        if pdf.get_y() + row_h > pdf.h - MARGIN:
            pdf.add_page()

        y_start = pdf.get_y()
        if i == 0:
            pdf.set_font("Helvetica", "B", 8)
        else:
            pdf.set_font("Helvetica", size=8)

        for j, cell in enumerate(row):
            pdf.set_xy(MARGIN + j * col_w, y_start)
            if i == 0:
                pdf.set_fill_color(*TABLE_HDR)
                pdf.set_text_color(*WHITE)
                pdf.set_font("Helvetica", "B", 8)
            elif i % 2 == 0:
                pdf.set_fill_color(*TABLE_ALT)
                pdf.set_text_color(*BLACK)
                pdf.set_font("Helvetica", size=8)
            else:
                pdf.set_fill_color(*WHITE)
                pdf.set_text_color(*BLACK)
                pdf.set_font("Helvetica", size=8)
            pdf.multi_cell(col_w, line_h, ascii_safe(cell), border=1, fill=True,
                           align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_xy(MARGIN, y_start + row_h)
    pdf.ln(3)


def parse_and_render(pdf, md_text):
    lines = md_text.split("\n")
    i = 0
    in_code = False
    code_lines = []
    table_rows = []

    while i < len(lines):
        line = lines[i]

        # Code fences
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                render_code(pdf, code_lines)
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Table rows
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r"^[-:]+$", c) for c in cells):
                i += 1
                continue
            cells = [re.sub(r"`([^`]+)`", r"\1", c) for c in cells]
            table_rows.append(cells)
            i += 1
            if i >= len(lines) or not lines[i].startswith("|"):
                render_table(pdf, table_rows)
                table_rows = []
            continue

        if table_rows:
            render_table(pdf, table_rows)
            table_rows = []

        # H1
        if re.match(r"^# [^#]", line):
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 20)
            pdf.set_text_color(*BLUE)
            pdf.ln(4)
            pdf.multi_cell(TEXT_W, 10, ascii_safe(line[2:].strip()),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
            i += 1
            while i < len(lines) and lines[i].startswith("**"):
                meta = re.sub(r"\*\*([^*]+)\*\*", r"\1", lines[i]).strip()
                pdf.set_font("Helvetica", size=9)
                pdf.set_text_color(100, 100, 100)
                pdf.multi_cell(TEXT_W, 5, ascii_safe(meta),
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                i += 1
            pdf.ln(4)
            pdf.set_draw_color(*BLUE)
            pdf.set_line_width(0.5)
            pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
            pdf.ln(4)
            continue

        # H2
        if re.match(r"^## [^#]", line):
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(*BLUE)
            pdf.ln(4)
            pdf.multi_cell(TEXT_W, 8, ascii_safe(line[3:].strip()),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(180, 200, 230)
            pdf.set_line_width(0.3)
            pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
            pdf.ln(3)
            i += 1
            continue

        # H3
        if re.match(r"^### [^#]", line):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(60, 60, 60)
            pdf.ln(2)
            pdf.multi_cell(TEXT_W, 7, ascii_safe(line[4:].strip()),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)
            i += 1
            continue

        # H4
        if re.match(r"^#### [^#]", line):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(TEXT_W, 6, ascii_safe(line[5:].strip()),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 1
            continue

        # HR
        if line.strip() in ("---", "***", "___"):
            pdf.set_draw_color(200, 200, 200)
            pdf.set_line_width(0.2)
            pdf.line(MARGIN, pdf.get_y() + 2, PAGE_W - MARGIN, pdf.get_y() + 2)
            pdf.ln(4)
            i += 1
            continue

        # Bullets
        if re.match(r"^[*\-] ", line):
            text = line[2:].strip()
            text = re.sub(r"`([^`]+)`", r"\1", text)
            text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
            text = re.sub(r"\*([^*]+)\*", r"\1", text)
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(*BLACK)
            pdf.set_x(MARGIN + 4)
            x_save = pdf.get_x()
            y_save = pdf.get_y()
            pdf.cell(4, 5, "-")
            pdf.multi_cell(TEXT_W - 8, 5, ascii_safe(text),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            text = re.sub(r"\*\*([^*]+)\*\*", r"\1", line[2:]).strip()
            pdf.set_fill_color(255, 250, 225)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(100, 80, 0)
            pdf.set_x(MARGIN + 4)
            pdf.multi_cell(TEXT_W - 4, 5, ascii_safe(text), fill=True,
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
            i += 1
            continue

        # Blank
        if not line.strip():
            pdf.ln(2)
            i += 1
            continue

        # Plain paragraph
        text = re.sub(r"`([^`]+)`", r"\1", line)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        if text.strip():
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(TEXT_W, 5, ascii_safe(text.strip()),
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        i += 1


def main():
    md_text = MD_PATH.read_text(encoding="utf-8")
    pdf = PDF()
    pdf.set_title("Gen-Health Analytics - Test Data and Testing Guide")
    pdf.set_author("Gen-Health Analytics")
    parse_and_render(pdf, md_text)
    pdf.output(str(PDF_PATH))
    print("PDF written to: " + str(PDF_PATH))


if __name__ == "__main__":
    main()
