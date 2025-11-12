import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import create_document
from schemas import Lead

# Optional providers
from typing import Tuple

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _owner_contacts() -> Tuple[str, str]:
    """Return (owner_email, owner_whatsapp_to) with sensible defaults."""
    owner_email = os.getenv("OWNER_EMAIL", "krishpersonal6@gmail.com")
    owner_wa = os.getenv("OWNER_WHATSAPP_TO", "+917668222021")
    return owner_email, owner_wa


def send_email_via_sendgrid(subject: str, body: str) -> bool:
    """Send an email using SendGrid if configured. Returns True on attempt, False if not configured."""
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL") or os.getenv("OWNER_EMAIL") or "krishpersonal6@gmail.com"
    to_email, _ = _owner_contacts()

    if not api_key:
        return False

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        sg = sendgrid.SendGridAPIClient(api_key)
        message = Mail(from_email=from_email, to_emails=to_email, subject=subject, html_content=body.replace("\n", "<br>"))
        sg.send(message)
        return True
    except Exception as e:
        # Swallow errors to not block lead creation
        return False


def send_whatsapp_via_twilio(message: str) -> bool:
    """Send a WhatsApp message using Twilio if configured. Returns True if attempted."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.getenv("TWILIO_WHATSAPP_FROM")  # e.g., 'whatsapp:+14155238886' for sandbox
    _, to_phone = _owner_contacts()
    to_whatsapp = f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone

    if not (account_sid and auth_token and from_whatsapp):
        return False

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(from_=from_whatsapp, to=to_whatsapp, body=message)
        return True
    except Exception:
        return False


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    # Email/WhatsApp provider availability
    response["email_provider"] = "✅ SendGrid" if os.getenv("SENDGRID_API_KEY") else "❌ Not Configured"
    response["whatsapp_provider"] = "✅ Twilio" if (os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN") and os.getenv("TWILIO_WHATSAPP_FROM")) else "❌ Not Configured"
    
    return response


@app.post("/api/leads")
def create_lead(lead: Lead):
    try:
        lead_id = create_document("lead", lead)

        # Compose notification text
        subject = "New IronPulse Lead"
        text = (
            f"New gym lead\n"
            f"Name: {lead.name}\n"
            f"Phone: {lead.phone}\n"
            f"Email: {lead.email or '-'}\n"
            f"Plan: {lead.selected_plan or '-'}\n"
            f"Message: {lead.message or '-'}\n"
            f"Source: {lead.source or 'web'}\n"
            f"Lead ID: {lead_id}"
        )

        # Attempt to send notifications (non-blocking for errors)
        email_sent = send_email_via_sendgrid(subject, text)
        wa_sent = send_whatsapp_via_twilio(text)

        return {"ok": True, "id": lead_id, "email_sent": email_sent, "whatsapp_sent": wa_sent}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
