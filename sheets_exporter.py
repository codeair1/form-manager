import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import inspect, text

def sync_db_to_sheet(db, table_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # 1. Setup Google Client
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
        client = gspread.authorize(creds)
        
        # 2. Get the Base Data from PostgreSQL
        inspector = inspect(db.engine)
        # Get all columns EXCEPT the 'responses' JSON column
        base_columns = [col['name'] for col in inspector.get_columns(table_name) if col['name'] != 'responses']
        
        # 3. Fetch rows and convert to dictionaries immediately
        result = db.session.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        
        # Convert SQLAlchemy Row objects to standard Python dictionaries
        parsed_rows = [row._asdict() for row in rows]

        # 4. Extract all unique question keys from the JSON column
        all_questions = []
        for p_row in parsed_rows:
            resp = p_row.get('responses', {})
            
            # Handle cases where responses might be a string instead of a dict
            if isinstance(resp, str):
                try:
                    resp = json.loads(resp)
                except:
                    resp = {}
            
            if resp:
                for question in resp.keys():
                    if question not in all_questions:
                        all_questions.append(question)

        # 5. Build final headers: [id, name, age...] + [q1, q2, q3...]
        final_headers = base_columns + all_questions
        bulk_data = [final_headers]
        
        # 6. Fill the data rows
        for p_row in parsed_rows:
            formatted_row = []
            
            # Part A: Add static columns (Full_name, Age, etc.)
            for col in base_columns:
                val = p_row.get(col, "")
                formatted_row.append(str(val) if val is not None else "")
            
            # Part B: Add dynamic question columns
            resp_dict = p_row.get('responses', {})
            if isinstance(resp_dict, str):
                try:
                    resp_dict = json.loads(resp_dict)
                except:
                    resp_dict = {}

            for q in all_questions:
                # If question exists, take value. If None or missing, leave empty string.
                val = resp_dict.get(q)
                formatted_row.append(str(val) if val is not None else "")
            
            bulk_data.append(formatted_row)

        # 7. Open/Create and Update
        try:
            spreadsheet = client.open(table_name)
        except gspread.exceptions.SpreadsheetNotFound:
            spreadsheet = client.create(table_name)
            spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')

        sheet = spreadsheet.sheet1
        sheet.clear() 
        sheet.update('A1', bulk_data)
        
        print(f"✅ Sync successful: {table_name} updated with flattened columns.")

    except Exception as e:
        print(f"❌ Sync Failed for {table_name}: {e}")