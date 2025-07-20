from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests, os, json
from supabase import create_client, Client

from auth import (
    get_user_state,
    set_user_state,
    get_user_email,
    set_user_email,
    get_user_otp,
    set_user_otp,
    generate_and_send_otp,
    is_authenticated,
    mark_authenticated,
    clear_user,
    set_user_intent,
    get_user_intent
)

from whatsapp import send_message, send_button_message
from ocr import ocr_from_bytes
from openai_utils import ask_openai
from datetime import datetime

app = FastAPI()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ACCESS_TOKEN = "EAAR4EKodEE4BPEdoHhdO0ckOAZBCFyE7dgr4nLmEAZCgyZAV1gmiFlktl7dNZARXoxQNVbNBjq0LmWrOpWZCbYRyuBNcHmkdBhKkFspA9WxajOkyTf9S9p8R9ZBFfQ9DJZBOmF3TMliH3xwpMWVzqFe8jFGZBCcuzbDhAPqNgajLJBZCyoxIJWrEmWFaCxksmZAX63lUjnoPYB1cqPwMoOSypTGXshzQYs0Am6u4ZBLJm4l6rjjEgZDZD"
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

def format_date(raw_date: str) -> str | None:
    try:
        return datetime.strptime(raw_date, "%d%m%Y").date().isoformat()
    except ValueError:
        return None

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print(json.dumps(data, indent=2))

    try:
        entry = data["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages")
        if not messages:
            return {"status": "ok"}

        msg = messages[0]
        sender = msg["from"]
        msg_type = msg["type"]

        if msg_type == "text":
            text = msg["text"]["body"]
            state = get_user_state(sender)

            if state == "awaiting_otp":
                if text == get_user_otp(sender):
                    email = get_user_email(sender)
                    result = supabase.table("users").select("email").eq("email", email).execute()

                    if result.data:
                        clear_user(sender)
                        mark_authenticated(sender)
                        send_message(sender, "✅ OTP verified and you're logged in!")
                        send_button_message(sender)
                    else:
                        set_user_state(sender, "awaiting_name")
                        send_message(sender, "👋 You're verified! Now please enter your full name to complete registration.")
                    return {"status": "ok"}
                else:
                    send_message(sender, "❌ Incorrect OTP. Try again.")
                    return {"status": "ok"}

            elif text.lower() == "hello":
                send_message(sender, "📧 Please enter your email for verification.")
                set_user_state(sender, "awaiting_email")
                return {"status": "ok"}

            elif state == "awaiting_email":
                set_user_email(sender, text)
                generate_and_send_otp(sender, text)
                send_message(sender, f"📨 OTP sent to {text}. Please reply with the code.")
                return {"status": "ok"}

            elif state == "awaiting_name":
                set_user_intent(sender, text.strip())
                set_user_state(sender, "awaiting_age")
                send_message(sender, "📅 Great. Please enter your age.")
                return {"status": "ok"}

            elif state == "awaiting_age":
                try:
                    age = int(text.strip())
                    set_user_otp(sender, str(age))
                    set_user_state(sender, "awaiting_gender")
                    send_message(sender, "👤 Got it. Lastly, enter your gender (e.g., Male/Female/Other).")
                except ValueError:
                    send_message(sender, "❌ Please enter a valid number for age.")
                return {"status": "ok"}

            elif state == "awaiting_gender":
                name = get_user_intent(sender)
                age = get_user_otp(sender)
                gender = text.strip()
                email = get_user_email(sender)

                supabase.table("users").insert({
                    "name": name,
                    "age": int(age),
                    "gender": gender,
                    "email": email,
                    "whatsapp": sender
                }).execute()

                clear_user(sender)
                mark_authenticated(sender)
                send_message(sender, f"✅ Thanks {name}! You're now registered and logged in.")
                send_button_message(sender)
                return {"status": "ok"}

            elif text.lower() == "status":
                send_message(sender, f"📌 State: {get_user_state(sender)} | Auth: {is_authenticated(sender)}")
                return {"status": "ok"}

            else:
                send_message(sender, "👋 Please type 'hello' to begin chat with FinBot!")
                return {"status": "ok"}

        if not is_authenticated(sender):
            send_message(sender, "🔒 Please verify by saying 'hello' first.")
            return {"status": "ok"}

        if msg_type == "interactive":
            button_id = msg["interactive"]["button_reply"]["id"]
            set_user_intent(sender, button_id)

            if button_id == "upload_invoice":
                send_message(sender, "📤 Please upload your invoice (PDF or image).")
            elif button_id == "upload_cheque":
                send_message(sender, "📤 Please upload a scanned cheque.")
            return {"status": "ok"}

        if msg_type in ["image", "document"]:
            intent = get_user_intent(sender)
            if intent not in ["upload_invoice", "upload_cheque"]:
                send_message(sender, "❗ Please select an option first using the buttons.")
                return {"status": "ok"}

            media_id = msg[msg_type]["id"]
            meta_url = f"https://graph.facebook.com/v19.0/{media_id}"
            meta = requests.get(meta_url, params={"access_token": ACCESS_TOKEN}).json()
            media_url = meta.get("url")

            if not media_url:
                print("❌ Failed to get media URL:", meta)
                send_message(sender, "⚠️ Failed to download your file. Please try again.")
                return {"status": "ok"}

            try:
                file_bytes = requests.get(media_url, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}).content
            except Exception as e:
                print("❌ Error downloading file:", e)
                send_message(sender, "⚠️ Failed to download your file.")
                return {"status": "ok"}

            try:
                ocr_text = ocr_from_bytes(file_bytes)
            except Exception as e:
                send_message(sender, "❌ OCR failed. Please upload a clear image or PDF.")
                return {"status": "ok"}

            if intent == "upload_invoice":
                prompt = f"""
                    You are an intelligent OCR post-processor for invoices.

                    Extract the following fields clearly from the raw OCR text below:
                    - Invoice Number
                    - Seller Name
                    - Buyer Name
                    - Invoice Date
                    - Item(s)
                    - Quantity
                    - Amount (Total)

                    If any field is missing or unclear, write "Not Found".

                    OCR Text:
                    \"\"\"{ocr_text}\"\"\"

                    Return the output in this format:
                    Invoice Number: ...
                    Seller Name: ...
                    Buyer Name: ...
                    Invoice Date: ...
                    Items:
                    - Item: ...
                        Quantity: ...
                        Amount: ...
                    Total Amount: ...
                """
            elif intent == "upload_cheque":
                prompt = f"""
                    You are an intelligent OCR post-processor for Indian bank cheques.

                    Extract these fields:
                    - Receiver Name (after "PAY")
                    - Account Holder Name (near signature)
                    - Cheque Date (top right, DDMMYYYY)
                    - Bank Name (top left)
                    - Account Number (near amount or A/c No.)
                    - Amount (in numerals)

                    Ignore static text like "OR BEARER", "Rupees", etc.

                    OCR Text:
                    \"\"\"{ocr_text}\"\"\"

                    Return the result in this format:

                    Account Holder Name: ...
                    Receiver Name: ...
                    Cheque Date: ...
                    Bank Name: ...
                    Account Number: ...
                    Amount: ...
                """
            else:
                raise ValueError(f"❌ Unknown intent: {intent}")

            try:
                response_text = ask_openai(prompt)
                send_message(sender, response_text)
            
                email = get_user_email(sender)
                lines = response_text.splitlines()
            
                if intent == "upload_invoice":
                    invoice_data = {
                        "email": email,
                        "invoice_number": "Not Found",
                        "sellers_name": "Not Found",
                        "buyers_name": "Not Found",
                        "date": None,
                        "item": "Not Found",
                        "quantity": None,
                        "amount": None,
                    }
            
                    for line in lines:
                        if line.startswith("Invoice Number:"):
                            invoice_data["invoice_number"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Seller Name:"):
                            invoice_data["sellers_name"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Buyer Name:"):
                            invoice_data["buyers_name"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Invoice Date:"):
                            raw_date = line.split(":", 1)[1].strip()
                            invoice_data["date"] = format_date(raw_date)
                        elif line.strip().startswith("- Item:"):
                            invoice_data["item"] = line.split(":", 1)[1].strip()
                        elif line.strip().startswith("Quantity:"):
                            qty = line.split(":", 1)[1].strip()
                            invoice_data["quantity"] = int(qty) if qty.isdigit() else None
                        elif line.strip().startswith("Amount:") or line.strip().startswith("Total Amount:"):
                            amt = line.split(":", 1)[1].strip().replace(",", "").replace("₹", "")
                            invoice_data["amount"] = int(float(amt)) if amt.replace('.', '').isdigit() else None
            
                    supabase.table("upload_invoice").insert(invoice_data).execute()
            
                elif intent == "upload_cheque":
                    cheque_data = {
                        "email": email,
                        "payee_name": "Not Found",
                        "senders_name": "Not Found",
                        "amount": None,
                        "date": None,
                        "bank_name": "Not Found",
                        "account_number": None,
                    }
            
                    for line in lines:
                        if line.startswith("Receiver Name:"):
                            cheque_data["payee_name"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Account Holder Name:"):
                            cheque_data["senders_name"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Cheque Date:"):
                            raw_date = line.split(":", 1)[1].strip()
                            cheque_data["date"] = format_date(raw_date)
                        elif line.startswith("Bank Name:"):
                            cheque_data["bank_name"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Account Number:"):
                            acc = line.split(":", 1)[1].strip().replace(" ", "")
                            cheque_data["account_number"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Amount:"):
                            amt = line.split(":", 1)[1].strip().replace(",", "").replace("₹", "")
                            cheque_data["amount"] = int(float(amt)) if amt.replace('.', '').isdigit() else None
            
                    supabase.table("upload_cheique").insert(cheque_data).execute()
            
                send_message(sender, "✅ Your document has been uploaded successfully.")
            
            except Exception as e:
                print("❌ Error during OCR or DB insert:", e)
                send_message(sender, "⚠ Failed to understand or store the document. Try again.")

    except Exception as e:
        print("Unhandled error:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

    return {"status": "ok"}
