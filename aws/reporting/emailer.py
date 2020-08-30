from smtplib import SMTP_SSL as SMTP
from email.mime.text import MIMEText

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
            print(sender)
            print(receivers)
        except Exception as e:
            print(str(e))
        finally:
            self.conn.quit()
        