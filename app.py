from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, String, MetaData, insert
import os
import requests

from form_generator.generator_form import create_omr
from process_omr import process_omr_pdf

app = Flask(__name__)
CORS(app)

# --- 1. Database Configuration (Consolidated) ---
# Replace with your actual password
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost:5432/test'
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

# --- 4. Dynamic Route (New Form & Table Creation) ---
@app.route('/new_form', methods=['POST'])
def new_form():
    try:
        request_json = request.json
        survey_data = request_json.get('survey_data')
        form_name = request_json.get('form_name', 'Untitled_Form')

        # Sanitize Table Name
        safe_table_name = "".join([c for c in form_name if c.isalnum() or c == '_']).lower().rstrip()
        table_name = f"{safe_table_name}_table"

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
        font_pth = r'C:\College\cep\HackStack\my-project\form_generator\fonts\NotoSans-Italic-VariableFont_wdth,wght.ttf'
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



@app.route('/api/upload', methods=['POST'])
def upload():
    file = request.files.get('image')
    if file:
        temp_path = "temp_omr.png"
        file.save(temp_path)
        
        try:
            # This import is fine as long as process_omr.py 
            # doesn't try to import 'app' back!
            from process_omr import process_omr_pdf
            
            # Run the logic
            results = process_omr_pdf(temp_path)
            
            return jsonify({"status": "success", "data": results})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"error": "No file uploaded"}), 400


@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)