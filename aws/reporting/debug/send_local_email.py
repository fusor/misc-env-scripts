import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from emailer import Emailer

emailer = Emailer(
    os.environ['SMTP_ADDR'],
    os.environ['SMTP_USERNAME'],
    os.environ['SMTP_PASSWORD'],
)
emailer.send_email(
    os.environ['SMTP_SENDER'],
    [os.environ['SMTP_RECEIVERS']],
    'Test - AWS Cleanup Notification',
    '<b>This is a test email.</b> If you see this, SMTP credentials are working.'
)
print("Test email sent (check your inbox)")
