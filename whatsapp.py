import requests
import os
from auth import set_user_intent

ACCESS_TOKEN = "EAAR4EKodEE4BPEdoHhdO0ckOAZBCFyE7dgr4nLmEAZCgyZAV1gmiFlktl7dNZARXoxQNVbNBjq0LmWrOpWZCbYRyuBNcHmkdBhKkFspA9WxajOkyTf9S9p8R9ZBFfQ9DJZBOmF3TMliH3xwpMWVzqFe8jFGZBCcuzbDhAPqNgajLJBZCyoxIJWrEmWFaCxksmZAX63lUjnoPYB1cqPwMoOSypTGXshzQYs0Am6u4ZBLJm4l6rjjEgZDZD"
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GRAPH_API_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def send_message(to: str, message: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
    print(response.json())

def send_button_message(to: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "Welcome to FinBot! What would you like to do?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "upload_cheque",
                            "title": "📓 Upload Cheque"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "upload_invoice",
                            "title": "💼 Upload Invoice"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "chat_finance",
                            "title": "💬 Chat"
                        }
                    }
                ]
            }
        }
    }
    response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
    print(response.json())     

def handle_button_click(to: str, button_id: str):
    set_user_intent(to, button_id)

    if button_id == "upload_cheque":
        send_message(to, "📝 Please upload a clear photo or PDF of your cheque.")
    elif button_id == "upload_invoice":
        send_message(to, "🧾 Please upload your invoice document.")
    elif button_id == "chat_finance":
        send_message(to, "💬 Ask me anything finance-related!")
    else:
        send_message(to, "❌ Invalid choice. Please try again.")
