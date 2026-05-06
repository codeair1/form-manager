from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def create_omr(filename, data, font_path, form_name):
    font_name_tag = "UnicodeFont"
    pdfmetrics.registerFont(TTFont(font_name_tag, font_path))
    
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    left_margin = 50
    right_margin = width - 50
    max_content_width = right_margin - left_margin

        # --- Header ---
    marker_size = 20
    marker_size = 20
    # --- Header ---
    c.setFillColorRGB(0, 0, 0)
    c.rect(0, height - 20, marker_size, marker_size, fill=1)
    c.setFont(font_name_tag, 18)
    c.drawCentredString(width/2, height - 40, form_name.upper())
    c.setFont(font_name_tag, 10)
    c.drawString(left_margin, height - 70, f"Full Name {'_'*76}")
    c.drawString(left_margin, height - 90, f"Age {'_'*10}")
    c.drawString(left_margin + 90, height - 90, f"Contact Number {'_'*40}")
    c.drawRightString(right_margin, height - 70, "Date ____/____/____")
    c.drawString(left_margin, height - 110, "Gender")

# Male option
    c.circle(left_margin + 70, height - 107, 5)  # circle
    c.drawString(left_margin + 80, height - 110, "Male")

    # Female option
    c.circle(left_margin + 140, height - 107, 5)
    c.drawString(left_margin + 150, height - 110, "Female")

    # Others 
    c.circle(left_margin + 210, height - 107, 5)
    c.drawString(left_margin + 220, height - 110, "Others")

    c.line(left_margin, height - 125, right_margin, height - 125)

    y_pos = height - 155 

    for idx, item in enumerate(data, start=1):
        # Page Overflow Check
        if y_pos < 100:
            c.showPage()
            y_pos = height - 60

        # --- 1. Question Wrapping (Left Aligned) ---
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
        y_pos -= 20 

        # --- 2. Options Logic (Left Aligned) ---
        c.setFont(font_name_tag, 9)
        option_gap = 25  # Space between options in the same row
        bubble_size = 5
        text_offset = 12 # Distance from bubble center to text start
        
        # We group options into rows that fit within the page width
        rows = [[]]
        curr_row_w = 0

        for opt in item['options']:
            text_to_wrap = opt if (opt and opt.strip()) else " "
            opt_lines = []
            remaining_text = text_to_wrap
            
            # Character-level wrapping for very long options (limited to 140px wide)
            max_opt_width = 140 
            while remaining_text:
                char_count = 0
                while char_count < len(remaining_text) and \
                      pdfmetrics.stringWidth(remaining_text[:char_count+1], font_name_tag, 9) < max_opt_width:
                    char_count += 1
                if char_count == 0: char_count = 1 
                opt_lines.append(remaining_text[:char_count])
                remaining_text = remaining_text[char_count:]

            widths = [pdfmetrics.stringWidth(l, font_name_tag, 9) for l in opt_lines]
            block_w = max(widths) if widths else 20
            # Total width of one option = Bubble + Space + Text Width
            total_opt_w = (bubble_size * 2) + text_offset + block_w

            if curr_row_w + total_opt_w + option_gap > max_content_width:
                rows.append([{"lines": opt_lines, "width": total_opt_w, "text_w": block_w}])
                curr_row_w = total_opt_w + option_gap
            else:
                rows[-1].append({"lines": opt_lines, "width": total_opt_w, "text_w": block_w})
                curr_row_w += total_opt_w + option_gap

        # --- 3. Draw the Options (Left Aligned) ---
        for row in rows:
            draw_x = left_margin + 15 # Slight indent for options
            max_lines_in_row = max(len(b['lines']) for b in row)

            for block in row:
                # Draw Bubble
                bubble_center_x = draw_x + bubble_size
                c.circle(bubble_center_x, y_pos, bubble_size, stroke=1, fill=0)
                
                # Draw Wrapped Text next to bubble
                line_y = y_pos - 3 # Align text vertically with bubble
                for line_text in block['lines']:
                    c.drawString(bubble_center_x + text_offset, line_y, line_text)
                    line_y -= 12 
                
                draw_x += block['width'] + option_gap
            
            # Move Y down based on tallest option in the row
            y_pos -= (max_lines_in_row * 12) + 10

        y_pos -= 15 # Space between questions

    c.save()