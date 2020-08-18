## To setup dependencies:
1. $ `virtualenv venv`
1. $ `source venv/bin/activate`
1. $ `pip install -r requirements.txt`


## Obtain credentials
1. Provide a `credentials.json` 
    * See: https://developers.google.com/sheets/api/guides/authorizing#APIKey
    * https://developers.google.com/sheets/api/quickstart/python
1. Run these scripts and if `token.pickle` is missing the scripts will prompt you to visit the link displayed and accept authorization
1. A token is then saved in `token.pickle`

## To run:
1. $ `source venv/bin/activate`
1. $ `python ./write_instance_report.py`

## To update dependencies:
1. pip install new packages as needed in development
1. $ `pip freeze > requirements.txt`
