import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()
SENDGRID_API_KEY = os.getenv("API_KEY")
SENDER_EMAIL = "sacrasticthinker@gmail.com"
RECEIVER_EMAIL = "Krishna@synapsebiopharma.com"

def send_email(new_items, subject="📰 Your News Alert"):
    # Build a friendly HTML body
    body = "<h2>Here are the latest news updates:</h2><ul>"
    for item in new_items:
        body += f"""
        <li>
            <strong>{item['date']}</strong> – {item['title']}<br>
            <a href="{item['link']}" target="_blank">🔗 Read more</a>
        </li><br>
        """
    body += "</ul><p>Stay informed,<br><em>Synapse News Tracker</em></p>"

    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=RECEIVER_EMAIL,
        subject=subject,
        html_content=body
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print("✅ Email sent successfully!")
    except Exception as e:
        print("❌ Error sending email:", e)
