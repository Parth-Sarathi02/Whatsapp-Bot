import random
import smtplib
from email.message import EmailMessage

EMAIL_USER = "dinoboyadi@gmail.com"
EMAIL_PASSWORD = "esahoznfsipmqjcq"

user_states = {}
user_emails = {}
user_otps = {}
user_intent = {}

authenticated_users = set()

def get_user_state(sender):
    return user_states.get(sender)

def set_user_state(sender, state):
    user_states[sender] = state

def set_user_email(sender, email):
    user_emails[sender] = email

def get_user_email(sender):
    return user_emails.get(sender)

def set_user_otp(sender, otp):
    user_otps[sender] = otp

def get_user_otp(sender):
    return user_otps.get(sender)

def clear_user(sender):
    user_states.pop(sender, None)
    user_otps.pop(sender, None)
    user_emails.pop(sender, None)

def mark_authenticated(sender):
    authenticated_users.add(sender)
    set_user_state(sender, "authenticated")

def is_authenticated(sender):
    return sender in authenticated_users

def send_otp_email(to_email: str, otp: str):
    msg = EmailMessage()
    msg.set_content(f"Your FinBot verification code is: {otp}")
    msg["Subject"] = "Your FinBot OTP Code"
    msg["From"] = EMAIL_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Email error: {e}")

def generate_and_send_otp(sender, email):
    otp = str(random.randint(100000, 999999))
    set_user_otp(sender, otp)
    set_user_state(sender, "awaiting_otp")
    send_otp_email(email, otp)

def set_user_intent(sender, intent):
    user_intent[sender] = intent

def get_user_intent(sender):
    return user_intent.get(sender, "unknown")
