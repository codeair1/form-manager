from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import psycopg2
import time
import os
import requests
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)

#Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='test'
    )
    return conn

#Initialize database
def init_db():
    retries = 5
    while retries > 0:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                )
            ''')
            conn.commit()
            cur.close()
            conn.close()
            print('Database initialized')
            break
        except Exception as e:
            print(f'Database connection failed, retrying... ({retries} left)')
            retries -= 1
            time.sleep(2)

init_db()

#Routes
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'message': 'working fine!'})

@app.route('/api/items', methods=['GET'])
def get_items():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM items')
    items = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{'id': item[0], 'name': item[1]} for item in items])

@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.json
    name = data.get('name')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO items (name) VALUES (%s) RETURNING id, name', (name,))
    item = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'id': item[0], 'name': item[1]})


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/create')
def create_page():
    return render_template('create_item.html')

@app.route('/api/upload', methods=['POST'])
def upload_image():
    file = request.files.get('image')

    if not file:
        return {"error": "No file"}, 400
    
    file.stream.seek(0)
    
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file": (
                file.filename,         
                file.stream,          
                file.content_type      
            )},
        data={
            "apikey": "K88904408288957",
            "language": "eng"
        }
    )

    result = response.json()
    print(result)
    return jsonify(result)

@app.route('/api/omr', methods=['POST'])
def omr():
    file = request.files.get('image')

    if not file:
        return {"error": "No file"}, 400

    npimg = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 🔥 blur for noise
    blurred = cv2.GaussianBlur(gray, (5,5), 0)

    # 🔥 adaptive threshold (better for uneven lighting)
    thresh = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2
    )

    # 🔥 detect circles instead of contours
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=30,
        param1=50,
        param2=30,
        minRadius=5,
        maxRadius=15
    )
    
    results = []

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")

        for (x, y, r) in circles:
            # ✅ safe ROI (avoid out of bounds)
            x1 = max(0, x - r)
            y1 = max(0, y - r)
            x2 = min(gray.shape[1], x + r)
            y2 = min(gray.shape[0], y + r)

            roi_thresh = thresh[y1:y2, x1:x2]
            roi_gray = gray[y1:y2, x1:x2]

            if roi_thresh.size == 0:
                continue

            # ✅ ink detection
            ink_ratio = cv2.countNonZero(roi_thresh) / roi_thresh.size
            mean_val = np.mean(roi_gray)

            # 🔥 tuned for tick marks
            checked = (ink_ratio > 0.15) and (mean_val < 185)

            results.append({
                "x": int(x),
                "y": int(y),
                "checked": bool(checked),
                "ink": float(ink_ratio),
                "mean": float(mean_val)
            })
            color = (0,255,0) if checked else (0,0,255)
            cv2.circle(img, (x, y), r, color, 2)

    results = sorted(results, key=lambda b: (b["y"], b["x"]))

    cv2.imwrite("debug.jpg", img)

    return {"boxes": results}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)