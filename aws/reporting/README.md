## To setup dependencies:
1. $ `virtualenv venv`
1. $ `source venv/bin/activate`
1. $ `pip install -r requirements.txt`


## Obtain credentials
These scripts use Google service account credentials to allow bots to run the scripts.

1. Create a new Service Account 
2. Create a new key in json format
3. Download the key to `credentials.json` file in the current directory

## To run:
1. $ `source venv/bin/activate`
1. $ `python ./write_instance_report.py`

## To update dependencies:
1. pip install new packages as needed in development
1. $ `pip freeze > requirements.txt`
