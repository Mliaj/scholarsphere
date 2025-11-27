from flask import render_template, current_app
from flask_mail import Message
from app import mail
from threading import Thread
import os

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            # In a real application, you'd want to log this error.
            print(f"Failed to send email: {e}")

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(
        subject,
        recipients=[to],
        sender=app.config['MAIL_USERNAME'] or 'noreply@scholarsphere.com'
    )
    
    # Render the HTML template
    msg.html = render_template(template, **kwargs)
    
    # Attach the logo
    logo_path = os.path.join(app.root_path, 'static/images/uc-logo.png')
    if os.path.exists(logo_path):
        with app.open_resource(logo_path) as fp:
            msg.attach(
                'uc-logo.png',
                'image/png',
                fp.read(),
                'inline',
                headers=[['Content-ID', '<logo>']]
            )

    # Send email in a separate thread
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
