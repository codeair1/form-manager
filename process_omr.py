import cv2
import numpy as np
import os
import pytesseract

# CRITICAL: Point this to your actual Tesseract installation path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def process_omr(file_path):
    # 1. Load the Image
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        from pdf2image import convert_from_path
        pages = convert_from_path(file_path, dpi=300)
        img = np.array(pages[0])
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img = cv2.imread(file_path)

    if img is None: 
        return {"error": "Failed to load image. Check the file path."}

    # 2. Define 'gray' IMMEDIATELY after loading
    # This ensures it exists for the rest of the function scope
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # 3. Detect Form Identity (Title at the very top)
    title_crop = gray[0:100, 0:img.shape[1]]
    detected_title = pytesseract.image_to_string(title_crop).strip()
    form_identity = "".join([c for c in detected_title if c.isalnum() or c == '_']).lower().split('\n')[0]

    if not form_identity:
        form_identity = "unknown_form"

    # 4. Detect Student Info (Name/Roll No)
    header_crop = gray[150:450, 0:img.shape[1]] 
    header_text = pytesseract.image_to_string(header_crop)
    
    student_name = "Unknown"
    roll_no = "Unknown"
    for line in header_text.split('\n'):
        if "Name" in line:
            student_name = line.split(':')[-1].replace('_', '').strip()
        if "Roll" in line:
            roll_no = line.split(':')[-1].replace('_', '').strip()

    # 5. Detect Circles
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
        param1=50, param2=30, minRadius=15, maxRadius=25
    )

    if circles is None:
        return {"error": "No OMR bubbles detected on the page."}

    circles = np.round(circles[0, :]).astype("int")
    circles = circles[circles[:, 1].argsort()]
    
    # 6. Group into Rows
    rows = []
    current_row = [circles[0]]
    for i in range(1, len(circles)):
        if abs(circles[i][1] - current_row[-1][1]) < 25:
            current_row.append(circles[i])
        else:
            current_row.sort(key=lambda x: x[0])
            rows.append(current_row)
            current_row = [circles[i]]
    rows.append(current_row)

    # 7. Process Answers
    final_responses = {}
    options_map = ["A", "B", "C", "D", "E"]

    for idx, row in enumerate(rows):
        # OCR Question Number
        bx, by, br = row[0]
        q_crop = gray[max(0, by-40):by+40, max(0, bx-160):bx-br-5]
        q_text = pytesseract.image_to_string(q_crop, config=r'--oem 3 --psm 6 digits').strip()
        q_num = "".join(filter(str.isdigit, q_text)) or str(idx + 1)

        # Detect marked bubble
        pixel_counts = []
        for (x, y, r) in row:
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.circle(mask, (x, y), r - 2, 255, -1)
            total = cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask))
            pixel_counts.append(total)

        marked_idx = np.argmax(pixel_counts)
        final_responses[q_num] = options_map[marked_idx] if marked_idx < len(options_map) else "N/A"

    return {
        "form_identity": form_identity,
        "student_name": student_name,
        "roll_no": roll_no,
        "responses": final_responses
    }