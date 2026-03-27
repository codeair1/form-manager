import cv2
import numpy as np
from pdf2image import convert_from_path

def process_omr_pdf(pdf_path):
    img = cv2.imread(pdf_path)
    # 1. Convert PDF page to OpenCV image
    pages = convert_from_path(pdf_path, dpi=300)
    img = np.array(pages[0])
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Pre-processing: Blur and Threshold
    # We want to make the bubbles stand out
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # 3. Find Circles (Bubbles)
    # param1/param2 adjust sensitivity. 
    # minRadius/maxRadius should match your PDF bubble size
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
        param1=50, param2=30, minRadius=15, maxRadius=25
    )

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        
        # Sort circles top-to-bottom (by Y coordinate)
        circles = circles[circles[:, 1].argsort()]
        
        # Group circles into rows (if they share a similar Y coordinate)
        rows = []
        current_row = [circles[0]]
        for i in range(1, len(circles)):
            if abs(circles[i][1] - current_row[-1][1]) < 20:
                current_row.append(circles[i])
            else:
                # Sort the completed row left-to-right
                current_row.sort(key=lambda x: x[0])
                rows.append(current_row)
                current_row = [circles[i]]
        rows.append(current_row) # Add last row

        results = {}
        for idx, row in enumerate(rows, start=1):
            pixel_counts = []
            for (x, y, r) in row:
                # Create a mask for each bubble
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.circle(mask, (x, y), r-2, 255, -1)
                
                # Count non-zero pixels (the "ink") inside the bubble
                mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                total = cv2.countNonZero(mask)
                pixel_counts.append(total)

            # The bubble with the most "ink" is the marked one
            # You can map this back to your options (0=A, 1=B, etc.)
            marked_idx = np.argmax(pixel_counts)
            results[f"Question_{idx}"] = marked_idx
            
        return results

    return {"error": "No bubbles detected"}

# Integration into your Flask Route
