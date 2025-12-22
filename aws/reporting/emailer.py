from smtplib import SMTP_SSL as SMTP
from email.mime.text import MIMEText
import logging

logger = logging.getLogger(__name__)

class Emailer(object):
    def __init__(self, smtp_addr, username, password):
        self.conn = SMTP(smtp_addr)
        self.username = username
        self.password = password
        self.conn.set_debuglevel(False)

    def send_email(self, sender, receivers, subject, message):
        """ sends message from sender to receivers
        """
        msg = MIMEText(message, 'html')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ','.join(receivers)
        try:
            self.conn.login(self.username, self.password)
            self.conn.sendmail(sender, receivers, msg.as_string())
        except Exception as e:
            logger.error(str(e))   
        finally:
            self.conn.quit()
        