import os
import requests

AZURE_OCR_URL = os.getenv("AZURE_OCR_URL") 
AZURE_KEY = os.getenv("AZURE_KEY")

def ocr_from_bytes(file_bytes: bytes) -> str:
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/octet-stream"
    }

    try:
        response = requests.post(AZURE_OCR_URL, headers=headers, data=file_bytes)
        if response.status_code != 202:
            print("❌ Azure OCR submit error:", response.text)
            return f"❌ Azure OCR error: {response.text}"

        result_url = response.headers.get("Operation-Location")
        if not result_url:
            return "❌ Azure OCR error: Missing Operation-Location"

        import time
        for _ in range(10): 
            time.sleep(0.5)
            result = requests.get(result_url, headers={"Ocp-Apim-Subscription-Key": AZURE_KEY})
            result_json = result.json()
            status = result_json.get("status")

            if status == "succeeded":
                break
            elif status == "failed":
                return "❌ Azure OCR failed to analyze image."

        else:
            return "❌ Azure OCR timed out."

        extracted_text = []
        for page in result_json["analyzeResult"]["readResults"]:
            for line in page.get("lines", []):
                extracted_text.append(line["text"])

        return "\n".join(extracted_text) if extracted_text else "❌ No text detected."

    except Exception as e:
        print("❌ Azure OCR exception:", e)
        return f"❌ Azure OCR error: {e}"

