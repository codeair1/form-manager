

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics  # <--- THIS IS THE MISSING PIECE
from reportlab.pdfbase.ttfonts import TTFont
import os

def create_omr(filename, data, font_path, form_name):
    font_name_tag = "UnicodeFont"
    pdfmetrics.registerFont(TTFont(font_name_tag, font_path))
    
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    left_margin = 50
    right_margin = width - 50
    center_x = width / 2
    max_content_width = right_margin - left_margin

    # --- Header ---
    c.setFont(font_name_tag, 18)
    c.drawCentredString(center_x, height - 40, form_name.upper())
    c.setFont(font_name_tag, 10)
    c.drawString(left_margin, height - 70, f"Name: {'_'*30}")
    c.drawString(left_margin, height - 90, f"Roll No: {'_'*25}")
    c.drawRightString(right_margin, height - 70, "Date: ____/____/2026")
    c.drawRightString(right_margin, height - 90, "Section: _________")
    c.line(left_margin, height - 105, right_margin, height - 105)

    y_pos = height - 140 

    for idx, item in enumerate(data, start=1):
        # Page Overflow Check
        if y_pos < 150:
            c.showPage()
            y_pos = height - 60

        # --- 1. Question Wrapping (Strict) ---
        c.setFont(font_name_tag, 11)
        full_q = f"{idx}. {item['question']}"
        words = full_q.split(' ')
        line = ""
        for word in words:
            if pdfmetrics.stringWidth(line + word, font_name_tag, 11) < max_content_width:
                line += word + " "
            else:
                c.drawString(left_margin, y_pos, line.strip())
                y_pos -= 15
                line = "   " + word + " "
        c.drawString(left_margin, y_pos, line.strip())
        y_pos -= 30 

        # --- 2. Options "Flow" with Character-Level Wrapping ---
        c.setFont(font_name_tag, 9)
        padding = 30
        rows = [[]]
        curr_row_w = 0

        for opt in item['options']:
            # Handle empty or None options
            text_to_wrap = opt if (opt and opt.strip()) else " "
            opt_lines = []
            remaining_text = text_to_wrap
            
            # Character-level wrapping
            while remaining_text:
                char_count = 0
                while char_count < len(remaining_text) and \
                      pdfmetrics.stringWidth(remaining_text[:char_count+1], font_name_tag, 9) < 150:
                    char_count += 1
                
                if char_count == 0: char_count = 1 
                opt_lines.append(remaining_text[:char_count])
                remaining_text = remaining_text[char_count:]

            # Safe max width calculation
            widths = [pdfmetrics.stringWidth(line, font_name_tag, 9) for line in opt_lines]
            block_w = max(widths) if widths else 20
            
            # Row assignment
            if curr_row_w + block_w + padding > max_content_width:
                rows.append([{"lines": opt_lines, "width": block_w}])
                curr_row_w = block_w + padding
            else:
                rows[-1].append({"lines": opt_lines, "width": block_w})
                curr_row_w += block_w + padding

        # --- 3. Draw the Options ---
        for row in rows:
            row_total_w = sum(b['width'] for b in row) + (padding * (len(row) - 1))
            start_x = (width - row_total_w) / 2
            
            draw_x = start_x
            max_lines_in_row = max(len(b['lines']) for b in row)

            for block in row:
                bubble_x = draw_x + (block['width'] / 2)
                
                # Bubble position stays at the top of the text block
                c.circle(bubble_x, y_pos, 5, stroke=1, fill=0)
                
                # Draw each line of the wrapped option
                line_y = y_pos - 15
                for line_text in block['lines']:
                    c.drawCentredString(bubble_x, line_y, line_text)
                    line_y -= 12 # Move down for the next line of text
                
                draw_x += block['width'] + padding
            
            # Adjust y_pos based on how many lines were used in the tallest block
            y_pos -= (30 + (max_lines_in_row * 12))

        y_pos -= 30

    c.save()