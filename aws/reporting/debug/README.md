# How to run
1. Assumes that you created a virtual environment and have the requirements installed from "../requirements.txt"
2. `cp sample.env .env`
    * Edit `.env` and added your SMTP credentials
3. `source .env`
4. `python send_local_email.py`
5. If your credentials are working you will see an email sent to "SMTP_RECEIVERS"
