from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, String, MetaData, insert, inspect
import os
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
            Column('student_name', String(255)),
            Column('roll_no', String(100)),
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
    # 1. ONLY check for the image file
    file = request.files.get('image')
    
    if not file:
        return jsonify({"error": "No image file received"}), 400

    # Save temp file
    temp_path = os.path.join(os.getcwd(), f"temp_{file.filename}")
    file.save(temp_path)

    try:
        from process_omr import process_omr
        # 2. Run the OMR. It will detect the title (form_identity) itself
        scan_data = process_omr(temp_path)
        print(scan_data)
        if "error" in scan_data:
            return jsonify({"error": scan_data["error"]}), 400

        # 3. Use the name DETECTED by the OCR script
        raw_identity = scan_data.get('form_identity')
        raw_identity = raw_identity.replace("_", "")
        target_table_name = f"{raw_identity}_responses"

        # 4. Check if the table exists
        inspector = db.inspect(db.engine)
        if target_table_name not in inspector.get_table_names():
            return jsonify({
                "error": f"Table '{target_table_name}' does not exist.",
                "detected_as": raw_identity
            }), 404

        # ... Insert logic ...

        metadata = MetaData()
        # Load the table structure from the database automatically
        target_table = Table(target_table_name, metadata, autoload_with=db.engine)

        # 6. Prepare the data for insertion
        # This matches the column names you created in your 'new_form' route
        stmt = insert(target_table).values(
            student_name=scan_data.get('student_name', 'Unknown'),
            roll_no=scan_data.get('roll_no', 'Unknown'),
            responses=scan_data.get('responses', {})  # This will be stored as JSON
        )

        # 7. Execute and Commit
        db.session.execute(stmt)
        db.session.commit()
        
        return jsonify({"status": "success", "data": scan_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)


@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)