import gspread
from oauth2client.service_account import ServiceAccountCredentials

@app.route('/api/export_to_sheets', methods=['POST'])
def export_to_sheets():
    data = request.json
    form_name = data.get('form_name')
    sheet_name = data.get('sheet_name') # This is the "name_responses" from JS

    try:
        # 1. Fetch data from your PostgreSQL (mydb/test)
        # Using your existing logic to get rows for 'form_name'
        rows = db.session.execute(text(f"SELECT * FROM {form_name}")).fetchall()
        
        # 2. Setup Google Sheets API
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
        client = gspread.authorize(creds)

        # 3. Open the sheet (Make sure the Admin shared the sheet with the Service Account Email!)
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.get_worksheet(0)

        # 4. Prepare data for sheets (Headers + Rows)
        # ... logic to format your JSON responses into a list of lists ...
        
        return jsonify({"message": "Data synced successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500