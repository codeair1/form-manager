import os
import json
import base64
from mistralai.client import Mistral
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = "PTi82vsaj9TxFt0nak1S8vkdzySII73B"

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
}


def _encode_file(file_path: str) -> tuple[str, str]:
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = MIME_MAP.get(ext)
    if not mime_type:
        raise ValueError(f"Unsupported file type: {ext}")
    with open(file_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


def process_omr(file_path: str) -> dict:
    if not MISTRAL_API_KEY:
        return {"error": "MISTRAL_API_KEY is not set."}

    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}

    try:
        b64_data, mime_type = _encode_file(file_path)
    except ValueError as e:
        return {"error": str(e)}

    client = Mistral(api_key=MISTRAL_API_KEY)

    # ── Step 1: OCR ─────────────────────────────────────────────────────────
    try:
        data_uri = f"data:{mime_type};base64,{b64_data}"
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": data_uri,
            },
        )
        ocr_text = "\n\n".join(page.markdown for page in ocr_response.pages)
    except Exception as e:
        return {"error": f"Mistral OCR failed: {e}"}

    if not ocr_text.strip():
        return {"error": "Mistral OCR returned empty text."}

    print(f"[OCR DEBUG] file={file_path}")
    print(f"[OCR DEBUG] ocr_text=\n{ocr_text}")
    print(f"[OCR DEBUG] --- end ocr text ---")

    # ── Step 2: Chat ─────────────────────────────────────────────────────────
    parse_prompt = f"""You are an OMR (Optical Mark Recognition) data extraction specialist.
Your ONLY job is to extract ALL marked bubble responses and personal details from OCR text.

### BUBBLE MARKING RULES:
- ☑ or ✓ = this bubble IS marked = selected answer
- ☐ or □ = this bubble is NOT marked = not selected
- For each question, find which bubble is marked (☑) and record its option number:
  * First option (A or Good or Yes etc.) = 1
  * Second option (B or Average or No etc.) = 2  
  * Third option (C or Bad etc.) = 3
  * Fourth option (D) = 4

### QUESTION KEY RULES:
- If the question has descriptive text → use that text as the key
  Example: "1. How was the service?" → key = "How was the service?"
- If the question has NO text, just a number → use "Question N"
  Example: "2." with options A B C D → key = "Question 2"
- Number-only continuation pages like "12. ☐ A ☐ B ☐ C ☑ D" → key = "Question 12"

### CRITICAL INSTRUCTIONS:
1. Extract EVERY question that appears in the OCR text — do NOT skip any
2. If a question has no bubble marked (all ☐), skip it
3. The form title is the largest heading (# Title) — extract it lowercase with underscores
4. If NO title exists on this page, use "unknown" for form_identity
5. Personal details (Full_name, Age, Contact_Number, Gender) may not appear on continuation pages — use "Unknown" for missing fields
6. YOU MUST EXTRACT ALL QUESTIONS — if you see 11 questions, return 11 responses; if 7, return 7

### OCR TEXT:
{ocr_text}

### OUTPUT — return ONLY this JSON, no markdown, no explanation:
{{
  "form_identity": "title_here_or_unknown",
  "Full_name": "name_or_Unknown",
  "Age": "age_or_Unknown",
  "Contact_Number": "number_or_Unknown",
  "Gender": "Male_or_Female_or_Other_or_Unknown",
  "responses": {{
    "How was the service?": 1,
    "Question 2": 3,
    "Question 12": 4
  }}
}}"""

    try:
        chat_response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.0,  # ✅ 0 not 0.1 — deterministic, no hallucination
        )
        raw_text = chat_response.choices[0].message.content
    except Exception as e:
        return {"error": f"Mistral Chat parsing failed: {e}"}

    # ── Clean and parse JSON ─────────────────────────────────────────────────
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

    # ── Normalize and return ─────────────────────────────────────────────────
    return {
        "form_identity": result.get("form_identity", "unknown"),
        "Full_name":     result.get("Full_name", "Unknown"),
        "Age":           result.get("Age", "Unknown"),
        "Contact_Number":result.get("Contact_Number", "Unknown"),
        "Gender":        result.get("Gender", "Unknown"),
        "responses":     result.get("responses", {}),
    }