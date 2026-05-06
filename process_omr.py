import os
import json
import base64
from mistralai.client import Mistral
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "PTi82vsaj9TxFt0nak1S8vkdzySII73B")

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
        return {"error": "MISTRAL_API_KEY not set"}
    if not os.path.exists(file_path):
        return {"error": "File not found"}

    try:
        b64_data, mime_type = _encode_file(file_path)
    except ValueError as e:
        return {"error": str(e)}

    client = Mistral(api_key=MISTRAL_API_KEY)

    try:
        data_uri = f"data:{mime_type};base64,{b64_data}"
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url", "document_url": data_uri},
        )
        ocr_text = "\n\n".join(page.markdown for page in ocr_response.pages)
    except Exception as e:
        return {"error": f"OCR failed: {e}"}

    parse_prompt = f"""Extract data from this OMR OCR text into JSON:
1. form_identity: slugified title (replace spaces and special characters (-,/,%,$,#,&,*,^ and etc all) with _ and make it in lowercase)
2. Date: YYYY-MM-DD
3. Full_name: full name
4. Age: integer or null
5. Contact_Number: string
6. Gender: string
7. responses: {{question_in_numbers: option in A,B,C,D,E format only never give it in words}}
8. if any of the above field is empty or not found, return ""
9. if more than one option selected for a question then select the first one only and ignore the rest

OCR TEXT:
{ocr_text}

Return ONLY JSON:
{{
  "form_identity": "",
  "Date": null,
  "Full_name": "",
  "Age": null,
  "Contact_Number": "",
  "Gender": "",
  "responses": {{}}
}}"""

    try:
        chat_res = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.1,
        )
        raw = chat_res.choices[0].message.content
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(cleaned)
    except Exception:
        return {"error": "Parsing failed"}

    return {
        "form_identity": result.get("form_identity", ""),
        "Date": result.get("Date", None),
        "Full_name": result.get("Full_name", ""),
        "Age": result.get("Age", None),
        "Contact_Number": result.get("Contact_Number", ""),
        "Gender": result.get("Gender", ""),
        "responses": result.get("responses", {}),
    }
