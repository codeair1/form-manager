from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, String, MetaData, insert, inspect
import os
import json
import requests
from dotenv import load_dotenv

# Load sensitive keys from .env
load_dotenv()

from form_generator.generator_form import create_omr
from process_omr import process_omr

app = Flask(__name__)
CORS(app)

# --- 1. Database Configuration (Consolidated) ---
# Fetched from your .env file
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/test')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 2. Static Model (Your original 'items' table) ---
class Item(db.Model):
    __tablename__ = 'items'
    test = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

# Initialize the static database tables
with app.app_context():
    try:
        # This attempts to connect and execute a simple 'SELECT 1'
        db.session.execute(db.text('SELECT 1'))
        db.create_all()
        print("✅ Database connection successful and tables initialized.")
    except Exception as e:
        print(f"❌ DATABASE CONNECTION FAILED: {e}")
        # Optional: terminate the app if DB is required
        # import sys; sys.exit(1)

@app.route('/api/health', methods=['GET'])
def health():
    try:
        # Check if we can reach the database
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            'status': 'success',
            'message': 'API and Database are connected!',
            'database': 'Connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'API is running, but Database connection failed.',
            'error': str(e)
        }), 500
    

@app.route('/api/items', methods=['GET'])
def get_items():
    items = Item.query.all()
    return jsonify([{'test': item.test, 'name': item.name} for item in items])

@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.json
    new_item = Item(name=data.get('name'))
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'id': new_item.test, 'name': new_item.name})


@app.route('/new_form', methods=['POST'])
def new_form():
    try:
        request_json = request.json
        survey_data = request_json.get('survey_data')
        form_name = request_json.get('form_name', 'Untitled_Form')

        # Sanitize Table Name
        safe_table_name = "".join([c for c in form_name if c.isalnum() or c == '_']).lower().rstrip()
        table_name = f"{safe_table_name}_responses"
        # Dynamically Create Table using SQLAlchemy Core
        # This keeps it separate from the Item model but within the same DB
        new_table = Table(
            table_name, db.metadata,
            Column('id', Integer, primary_key=True),
            Column('Full_name', String(255)),
            Column('Age', String(100)),
            Column('Contact_Number', String(20)),
            Column('Gender', String(20)),
            Column('responses', db.JSON),
            extend_existing=True
        )
        

        db.metadata.create_all(db.engine)

        # PDF Generation Logic
        font_pth = r'E:\ngo\form-manager\form_generator\fonts\NotoSans-VariableFont_wdth,wght.ttf'
        output_dir = os.path.join(os.getcwd(), 'forms')
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        save_path = os.path.join(output_dir, f"{safe_table_name}.pdf")
        
        # Call the OMR Generator
        create_omr(save_path, survey_data, font_pth, form_name=form_name)
        
        return send_file(save_path, as_attachment=True)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return jsonify({"error": str(e)}), 500


# --- 4. Dynamic Route (New Form & Table Creation) ---
@app.route('/api/upload', methods=['POST'])
def upload():
    files = request.files.getlist('images')

    if not files:
        return jsonify({"error": "No image files received"}), 400

    from collections import defaultdict
    from process_omr import process_omr

    subfolder_map = defaultdict(list)
    all_temp_paths = []  # track all temp files for cleanup

    # ── Step 1: Save ALL files to disk immediately ──────────────────────────
    for file in files:
        print(f"[DEBUG] received filename: {file.filename}")
        if "__" in file.filename:
            folder_name, real_name = file.filename.split("__", 1)
        else:
            folder_name = "__root__"
            real_name = file.filename

        temp_path = os.path.normpath(
            os.path.join(os.getcwd(), f"temp_{folder_name}_{real_name}")
        )
        file.save(temp_path)
        size = os.path.getsize(temp_path)
        print(f"[DEBUG] saved → {temp_path} ({size} bytes)")

        subfolder_map[folder_name].append((temp_path, real_name))
        all_temp_paths.append(temp_path)

    print(f"[DEBUG] Subfolders: {list(subfolder_map.keys())}")
    print(f"[DEBUG] Files per subfolder: { {k: len(v) for k, v in subfolder_map.items()} }")

    results = []
    errors = []

    # ── Step 2: Process each subfolder ─────────────────────────────────────
    try:
        for folder_name, folder_entries in subfolder_map.items():

            # Sort by filename so page1 always comes before page2
            folder_entries.sort(key=lambda x: x[1])
            print(f"[{folder_name}] Processing {len(folder_entries)} image(s): {[e[1] for e in folder_entries]}")

            try:
                # ── Page 1: identity + first set of responses ───────────────
                first_image_path, _ = folder_entries[0]
                scan_data = process_omr(first_image_path)
                print(f"[{folder_name}] page1 scan_data: {scan_data}")

                if "error" in scan_data:
                    errors.append({"folder": folder_name, "error": scan_data["error"]})
                    continue

                raw_identity = scan_data.get('form_identity', '').replace("_", "")
                target_table_name = f"{raw_identity}_responses"

                inspector = db.inspect(db.engine)
                if target_table_name not in inspector.get_table_names():
                    errors.append({
                        "folder": folder_name,
                        "error": f"Table '{target_table_name}' does not exist.",
                        "detected_as": raw_identity
                    })
                    continue

                # ── Remaining pages: merge responses ────────────────────────
                all_responses = dict(scan_data.get('responses', {}))

                for page_idx, (temp_path, filename) in enumerate(folder_entries[1:], start=2):
                    size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                    print(f"[{folder_name}] page{page_idx} path={temp_path} | size={size} bytes")

                    extra_data = process_omr(temp_path)
                    print(f"[{folder_name}] page{page_idx} raw extra_data: {extra_data}")

                    if "error" in extra_data:
                        print(f"[{folder_name}] WARNING: OMR failed for {filename}: {extra_data['error']}")
                        continue

                    extra_responses = extra_data.get('responses', {})
                    print(f"[{folder_name}] page{page_idx} responses count: {len(extra_responses)}")

                    if not extra_responses:
                        print(f"[{folder_name}] WARNING: page{page_idx} returned empty responses")
                        continue

                    # Prefix duplicate keys with page number
                    for key, value in extra_responses.items():
                        unique_key = key if key not in all_responses else f"[P{page_idx}] {key}"
                        all_responses[unique_key] = value

                    print(f"[{folder_name}] After merging page{page_idx}: {len(all_responses)} total responses")

                print(f"[{folder_name}] Final responses ({len(all_responses)}): {list(all_responses.keys())}")

                # ── Insert into DB ──────────────────────────────────────────
                metadata = MetaData()
                target_table = Table(target_table_name, metadata, autoload_with=db.engine, extend_existing=True)
                table_columns = {col.name for col in target_table.columns}

                row_data = {
                    "Full_name":      scan_data.get("Full_name", "Unknown"),
                    "Age":            scan_data.get("Age", "Unknown"),
                    "Contact_Number": scan_data.get("Contact_Number", "Unknown"),
                    "Gender":         scan_data.get("Gender", "Other"),
                    "responses":      all_responses,
                }
                filtered_data = {k: v for k, v in row_data.items() if k in table_columns}

                if not filtered_data:
                    errors.append({
                        "folder": folder_name,
                        "error": "No matching columns found.",
                        "table_columns": list(table_columns)
                    })
                    continue

                stmt = insert(target_table).values(**filtered_data)
                db.session.execute(stmt)
                db.session.commit()

                results.append({
                    "folder":          folder_name,
                    "status":          "success",
                    "inserted_into":   target_table_name,
                    "pages_processed": len(folder_entries),
                    "total_responses": len(all_responses),
                    "data":            {**scan_data, "responses": all_responses},
                })

            except Exception as e:
                db.session.rollback()
                errors.append({"folder": folder_name, "error": str(e)})

    finally:
        # ── Step 3: Clean up ALL temp files once everything is done ─────────
        for temp_path in all_temp_paths:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"[DEBUG] cleaned up {temp_path}")

    return jsonify({
        "total_folders": len(subfolder_map),
        "successful":    len(results),
        "failed":        len(errors),
        "results":       results,
        "errors":        errors,
    }), 200

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)