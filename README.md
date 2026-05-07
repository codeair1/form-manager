# OMR Form Manager

Double Click on Form_Manager.bat to run application.


**Technical Documentation**
`v1.0  |  Flask + React + PostgreSQL + Google Sheets`

---


## Overview

The OMR Form Manager is a full-stack web application that automates the entire lifecycle of Optical Mark Recognition (OMR) feedback forms — from PDF creation to scanning, database storage, and spreadsheet export.

Built for institutions and organizations that collect large volumes of paper-based feedback, this system eliminates manual data entry by using AI-powered OCR (Mistral) to read scanned forms and automatically store results in a PostgreSQL database.

---

## System Architecture

| Layer | Stack |
|---|---|
| **Frontend** | React 18 — Single-page app with 3 views (Builder, Scanner, Downloader) |
| **Backend** | Flask (Python 3.11) — REST API on port 8000 with CORS enabled |
| **Database** | PostgreSQL 15 — Dynamic per-form tables with JSON response column |
| **AI/OCR** | Mistral AI — OCR + LLM parsing of scanned OMR sheet images |
| **Sheets** | Google Sheets API via gspread — Auto-sync to named spreadsheets |

---

## Project Structure

```
project-root/
├── app.py                    # Flask application & all API routes
├── process_omr.py            # Mistral OCR + LLM response parser
├── sheets_exporter.py        # Google Sheets sync logic
├── organize.py               # Black-mark based image folder organizer
├── requirements.txt          # Python dependencies
├── google_credentials.json   # Service account key (not in repo)
├── .env                      # Environment variables (not in repo)
├── forms/                    # Generated PDF output folder
├── form_generator/
│   ├── generator_form.py     # ReportLab PDF builder
│   └── fonts/                # NotoSans font files
└── frontend/
    └── src/App.js            # React single-page application
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 15 running locally
- Mistral AI API key
- Google Cloud service account with Sheets + Drive API enabled

### 1. Clone & Install Python Dependencies

```bash
git clone <your-repo-url>
cd project-root
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/test
MISTRAL_API_KEY=your_mistral_api_key_here
```

### 3. Google Sheets Credentials

Place your downloaded service account JSON key file in the project root as `google_credentials.json`. Then in `sheets_exporter.py`, replace the placeholder email with your Google account:

```python
spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')
```

### 4. Start the Backend

```bash
python app.py
# Flask runs on http://localhost:8000
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm start
# React runs on http://localhost:3000
```

---

## API Reference

### Health & Items

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/health` | Check API and database connectivity |
| `GET` | `/api/items` | List all items from the static items table |
| `POST` | `/api/items` | Create a new item in the static items table |

### Form Management

| Method | Route | Description |
|---|---|---|
| `POST` | `/new_form` | Generate a PDF form and create its DB response table |
| `POST` | `/api/upload` | Upload scanned images, run OCR, and insert results into DB |
| `GET` | `/api/rows/<form_name>` | Fetch all rows from a form's response table |
| `POST` | `/api/export_to_sheets` | Sync a form's DB table to a named Google Sheet |

### Route Details

#### POST `/new_form`

Creates a PDF OMR form and a corresponding PostgreSQL table to store responses.

**Request body:**
```json
{
  "form_name": "Patient Feedback",
  "survey_data": [
    { "question": "How was the service?", "options": ["Good", "Average", "Bad"] }
  ]
}
```

**Response:** PDF file download (binary)

**Side effects:** Creates table `<form_name>_responses` in PostgreSQL with columns: `id`, `Date`, `Full_name`, `Age`, `Contact_Number`, `Gender`, `responses` (JSON).

---

#### POST `/api/upload`

Accepts a multipart form upload of scanned OMR images. Each image is processed by Mistral OCR, parsed by an LLM, and the extracted data is inserted into the correct form's database table.

Expected filename format: `<subfolder>__<page_name>.jpg` — images in the same subfolder are treated as pages of one respondent's submission.

**Response:**
```json
{
  "total_folders": 3,
  "successful": 3,
  "failed": 0,
  "results": [{ "folder": "101", "status": "success", "inserted_into": "survey_responses" }],
  "errors": []
}
```

---

#### GET `/api/rows/<form_name>`

Returns all rows from `<form_name>_responses`. The `responses` column is returned as a parsed JSON object, not a raw string.

**Example:** `GET /api/rows/patient_feedback`

```json
{
  "rows": [
    {
      "id": 1,
      "Full_name": "John Doe",
      "Age": "25",
      "Contact_Number": "9876543210",
      "Gender": "Male",
      "responses": { "1": "A", "2": "C", "3": "B" }
    }
  ]
}
```

---

#### POST `/api/export_to_sheets`

Syncs a form's full database table to a Google Sheet. If the sheet already exists, it is cleared and rewritten — no duplicate sheets are created.

**Request body:**
```json
{
  "form_name": "patient_feedback",
  "sheet_name": "patient_feedback_responses"
}
```

---

## Data Flow

### Form Creation

1. User enters form name and questions in the React Builder
2. Frontend POSTs to `/new_form`
3. Backend sanitizes the name → creates `<name>_responses` table in PostgreSQL
4. ReportLab generates a PDF with bubbles, header, and identity fields
5. PDF is returned as a file download

### Scanning & Processing

1. User uploads a directory of scanned images via the Scanner view
2. Frontend renames files as `<subfolder>__<filename>` to encode grouping
3. Backend saves all files to disk first, then processes subfolder by subfolder
4. Page 1 of each subfolder: Mistral OCR extracts text, LLM parses identity + responses
5. Subsequent pages: responses are merged (duplicate keys prefixed with `[P2]`, `[P3]`, etc.)
6. Row is inserted into the matched `<form_identity>_responses` table
7. Temp files are cleaned up; Google Sheets is synced automatically

### Downloading Data

1. User enters form name in the Download Sheets view
2. Frontend fetches all rows via `GET /api/rows/<form_name>`
3. The `responses` JSON column is flattened — each question key becomes a column
4. User can preview the data in a scrollable table
5. Download CSV button generates and downloads a local CSV file

---

## Database Schema

### Dynamic Response Tables

Each form creates its own table named `<sanitized_form_name>_responses`:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-incremented primary key |
| `Date` | VARCHAR(20) | Date of form submission (YYYY-MM-DD) |
| `Full_name` | VARCHAR(255) | Respondent's full name |
| `Age` | VARCHAR(100) | Respondent's age |
| `Contact_Number` | VARCHAR(20) | Respondent's phone number |
| `Gender` | VARCHAR(20) | Male / Female / Others |
| `responses` | JSON | Map of question number to selected option e.g. `{"1": "A", "2": "C"}` |

### Table Naming Convention

Form names are sanitized before use as table names:

- All characters other than letters, digits, and underscores are removed
- Spaces are converted to underscores
- The name is lowercased
- `_responses` is appended as a suffix

**Example:** `"Patient Feedback (2024)"` → `patient_feedback_2024_responses`

---

## OMR Processing (`process_omr.py`)

This module handles the AI-powered reading of scanned OMR sheets. It is the core intelligence of the system.

### How It Works

1. Image is base64-encoded and sent to Mistral OCR (`mistral-ocr-latest`)
2. OCR returns markdown text from all pages
3. The OCR text is passed to `mistral-small-latest` with a structured prompt
4. The LLM extracts identity fields and maps question numbers to selected options
5. Result is returned as a clean Python dictionary

### Output Format

```json
{
  "form_identity": "patient_feedback",
  "Date": "2024-01-15",
  "Full_name": "Jane Smith",
  "Age": "32",
  "Contact_Number": "9876543210",
  "Gender": "Female",
  "responses": {
    "1": "A",
    "2": "C",
    "3": "B"
  }
}
```

### Supported File Types

`JPG`, `JPEG`, `PNG`, `WebP`, `GIF`, `PDF`

> ⚠️ **Note:** If more than one bubble is filled for a question, the LLM is instructed to select the **first option only** and ignore the rest.

---

## Image Organizer (`organize.py`)

A standalone utility that pre-processes a flat folder of scanned images into the subfolder structure required by the upload route.

### How It Works

1. Reads all images from the `scanned_images/` input folder
2. Sorts them by file modification time (preserving scan order)
3. Detects a black marker in the top-left 4×4 pixel region of each image
4. A new subfolder (named by roll number) is created whenever a black marker is found
5. Subsequent pages without a marker are added to the current student's folder
6. Output is written to `organized_output/`

### Usage

```bash
# Place scanned images in scanned_images/
python organize.py
# Output: organized_output/101/, organized_output/102/, ...
```

### Configuration

```python
INPUT_FOLDER = 'scanned_images'
OUTPUT_FOLDER = 'organized_output'
START_ROLL = 101    # Starting roll number
```

---

## Google Sheets Integration

### `sheets_exporter.py`

The `sync_db_to_sheet(db, table_name)` function handles the full Sheets sync workflow:

1. Authenticates with the Google service account
2. Fetches all rows from the given PostgreSQL table
3. Collects all unique question keys from the `responses` JSON column across all rows
4. Builds a flat header row: `[id, Date, Full_name, Age, Contact_Number, Gender, Q1, Q2, ...]`
5. Writes all data starting at cell `A1`
6. Creates the spreadsheet if it does not exist; clears and rewrites it on subsequent calls

### When Sync Happens

- Automatically after each successful `/api/upload` scan
- On-demand via `POST /api/export_to_sheets` from the frontend

> 🔴 **Important:** Replace `'your-email@gmail.com'` in `sheets_exporter.py` with your actual Google account email to receive write access to newly created sheets.

---

## Frontend (React)

### Views

#### Home
Landing page with three navigation buttons: **Create New Form**, **Scan Feedbacks**, and **Download Sheets**.

#### Builder
Allows the user to name a form and add questions with configurable options. Submitting posts to `/new_form` and triggers a PDF download.

#### Scanner
Accepts a directory upload of scanned images. Files are renamed with their subfolder prefix before upload so the backend can group multi-page submissions. Results of the last scanned submission are shown after processing.

#### Download Sheets
Fetches all rows from a named form's response table and displays them in a scrollable preview table. Each question column is extracted from the `responses` JSON. A **Download CSV** button saves the data locally as a `.csv` file.

---

## Dependencies

### Python (`requirements.txt`)

| Package | Purpose |
|---|---|
| `Flask` | Web framework and REST API |
| `flask-cors` | Cross-origin request support |
| `flask-sqlalchemy` | ORM and DB session management |
| `SQLAlchemy` | Dynamic table creation and queries |
| `psycopg2-binary` | PostgreSQL adapter |
| `mistralai` | OCR and LLM API client |
| `gspread` + `oauth2client` | Google Sheets read/write |
| `reportlab` | PDF generation for OMR forms |
| `opencv-python` | Black mark detection in `organize.py` |
| `python-dotenv` | Environment variable loading |

### JavaScript

| Package | Purpose |
|---|---|
| `react 18` | UI library |
| `react-dom` | DOM rendering |
| `react-scripts` | CRA build tooling |
| `axios` | HTTP client (available but `fetch` used directly) |

---

## Known Issues & Notes

> ⏱️ **Rate Limiting:** A 2-second delay (`time.sleep(2)`) is added between each Mistral API call during upload processing to avoid rate limit errors. For large batches this will slow down processing.
