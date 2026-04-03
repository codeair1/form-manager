import os
import shutil
import cv2
import numpy as np

INPUT_FOLDER = "scanned_images"
OUTPUT_FOLDER = "organized_output"
START_ROLL = 101

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def is_image(file):
    return file.lower().endswith(('.png', '.jpg', '.jpeg'))

# 🔍 Detect black mark in top-left 4x4 region
def has_black_mark(image_path):
    img = cv2.imread(image_path)

    if img is None:
        return False

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 📍 Top-left 4x4 pixels
    roi = gray[0:4, 0:4]

    # Convert to binary (detect dark pixels)
    _, thresh = cv2.threshold(roi, 50, 255, cv2.THRESH_BINARY_INV)

    black_pixels = np.sum(thresh == 255)
    total_pixels = roi.size

    black_ratio = black_pixels / total_pixels

    # Since region is tiny → use stricter threshold
    return black_ratio > 0.5


# 📂 Step 1: Get all images
files = [f for f in os.listdir(INPUT_FOLDER) if is_image(f)]

# ⏱️ Step 2: Sort by time
files.sort(key=lambda x: os.path.getmtime(os.path.join(INPUT_FOLDER, x)))

print("Sorted files:")
for f in files:
    print(f)

print("\nProcessing...\n")

roll_no = START_ROLL
page_count = 0
student_folder = None

# 🔁 Step 3: Process each image
for idx, file in enumerate(files):
    src_path = os.path.join(INPUT_FOLDER, file)

    # 🆕 New student if first image OR black mark detected
    if idx == 0 or has_black_mark(src_path):
        student_folder = os.path.join(OUTPUT_FOLDER, str(roll_no))
        os.makedirs(student_folder, exist_ok=True)

        page_count = 1
        print(f"\n🆕 New student → Roll {roll_no}")

        roll_no += 1  # increment for next student

    else:
        page_count += 1

    # 💾 Save image into student folder
    dest_path = os.path.join(student_folder, f"page_{page_count}.jpg")
    shutil.copy(src_path, dest_path)

    print(f"{file} → {os.path.basename(student_folder)}/page_{page_count}.jpg")

print("\n✅ Done! Fully organized using top-left black mark detection.")