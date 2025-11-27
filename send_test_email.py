from app import app, mail
from flask_mail import Message

def send_test_email():
    with app.app_context():
        msg = Message(
            subject="Test Email from Scholarsphere",
            recipients=["test@example.com"],
            body="This is a test email to verify MailHog integration.",
            sender=app.config.get('MAIL_USERNAME') or 'noreply@scholarsphere.com'
        )
        try:
            mail.send(msg)
            print("Test email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_test_email()
