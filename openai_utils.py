import os
import requests

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

def ask_openai(prompt: str) -> str:
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_API_VERSION}"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }

    payload = {
        "messages": [
            {"role": "system", "content": "You are an invoice or cheque parser."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 500
    }
    
    try:
        print("Sending request to OpenAI...")
        response = requests.post(url, headers=headers, json=payload)
        print("Status:", response.status_code)
        print("Raw text:", response.text)

        response.raise_for_status()

        if not response.text:
            return "❌ OpenAI returned an empty response."

        try:
            result = response.json()
            print("✅ OpenAI Result:", result)

            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"]
            else:
                return "❌ No choices found in OpenAI response."

        except ValueError as json_err:
            print("❌ JSON Decode Error:", json_err)
            return f"❌ Failed to parse OpenAI response: {json_err}"

    except requests.exceptions.RequestException as e:
        print("❌ OpenAI error:", e)
        return f"❌ OpenAI error: {e}"


