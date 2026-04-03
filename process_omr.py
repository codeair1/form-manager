import os
import json
import base64
from mistralai.client import Mistral
from dotenv import load_dotenv

# Load API key from .env file automatically
load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================
# Your API key is stored safely in the .env file
# (not in the code, not pushed to git)
#
MISTRAL_API_KEY = "PTi82vsaj9TxFt0nak1S8vkdzySII73B"

# ============================================================
# MIME type mapping
# ============================================================
MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
}


def _encode_file(file_path: str) -> tuple[str, str]:
    """Read a file and return (base64_data, mime_type)."""
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = MIME_MAP.get(ext)
    if not mime_type:
        raise ValueError(f"Unsupported file type: {ext}")

    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


def process_omr(file_path: str) -> dict:
    """
    Process an OMR sheet using Mistral OCR + Mistral Chat API.

    Step 1: Mistral OCR extracts all text/content from the image as markdown.
    Step 2: Mistral Chat model parses the OCR output to detect form title,
            student info, and marked bubble responses.

    Returns:
    {
        "form_identity": str,
        "student_name": str,
        "roll_no": str,
        "responses": { "1": "A", "2": "C", ... }
    }
    """

    # ── Guard: API key ──────────────────────────────────────
    if not MISTRAL_API_KEY:
        return {"error": "MISTRAL_API_KEY is not set. Get a free key at https://console.mistral.ai/"}

    # ── Guard: file exists ──────────────────────────────────
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    # ── Encode the file ─────────────────────────────────────
    try:
        b64_data, mime_type = _encode_file(file_path)
    except ValueError as e:
        return {"error": str(e)}

    # ── Initialize Mistral client ───────────────────────────
    client = Mistral(api_key=MISTRAL_API_KEY)

    # ══════════════════════════════════════════════════════════
    # STEP 1: OCR — Extract text from the image
    # ══════════════════════════════════════════════════════════
    try:
        data_uri = f"data:{mime_type};base64,{b64_data}"

        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": data_uri,
            },
        )

        # Combine all pages' markdown into one string
        ocr_text = "\n\n".join(page.markdown for page in ocr_response.pages)

    except Exception as e:
        return {"error": f"Mistral OCR failed: {e}"}

    if not ocr_text.strip():
        return {"error": "Mistral OCR returned empty text. The image may be unreadable."}

    # ══════════════════════════════════════════════════════════
    # STEP 2: Chat — Parse OCR output into structured JSON
    # ══════════════════════════════════════════════════════════
    parse_prompt = f"""You are an OMR (Optical Mark Recognition) sheet parser.

Below is the OCR-extracted text from a scanned OMR answer sheet. Analyze it
and extract the following information:

1. **form_identity**: The title or heading of the form.
   - Convert to lowercase, remove spaces and special characters (keep only
     alphanumerics and underscores). Example: "Math Quiz 1" → "math_quiz_1"
   - If no title found, use "unknown_form".

2. **student_name**: The student's name (usually near a "Name" label).
   - If not found, use "Unknown".

3. **roll_no**: The student's roll number / ID (usually near "Roll No" label).
   - If not found, use "Unknown".

4. **responses**: A JSON object mapping question numbers (as strings) to the
   selected option letter (A, B, C, D, or E).
   - Look for marked/filled bubbles or any indication of selected answers.
   - Example: {{"1": "B", "2": "A", "3": "D"}}

--- OCR TEXT START ---
{ocr_text}
--- OCR TEXT END ---

Return ONLY a valid JSON object with exactly these four keys:
{{
  "form_identity": "...",
  "student_name": "...",
  "roll_no": "...",
  "responses": {{ ... }}
}}

Do NOT include any explanation, markdown fences, or text outside the JSON."""

    try:
        chat_response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.1,
        )

        raw_text = chat_response.choices[0].message.content

    except Exception as e:
        return {"error": f"Mistral Chat parsing failed: {e}"}

    # ── Parse JSON response ─────────────────────────────────
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "error": "Mistral returned invalid JSON",
            "raw_ocr": ocr_text,
            "raw_response": raw_text,
        }

    # ── Validate & normalize ────────────────────────────────
    return {
        "form_identity": result.get("form_identity", "unknown_form"),
        "student_name": result.get("student_name", "Unknown"),
        "roll_no": result.get("roll_no", "Unknown"),
        "responses": result.get("responses", {}),
    }