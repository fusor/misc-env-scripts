## To setup dependencies:
Setup Python [virtual environment](https://docs.python.org/3/library/venv.html)

1. Clone this repository
   ```
      git clone https://github.com/fusor/misc-env-scripts.git
   ```
2. Activate the virtual environment and install the required packages
   ```
      pip install -r requirements.txt
   ```

## Obtain credentials
These scripts use Google service account credentials to allow bots to run the scripts.

1. Create a new [Google Service Account](https://support.google.com/a/answer/7378726?hl=en)
2. Create a new key in json format
3. Download the key to `credentials.json` file in the current directory
4. Share the Google Sheet with the Google service account email.

<img width="1440" alt="Screen Shot 2022-05-24 at 11 25 36 AM" src="https://user-images.githubusercontent.com/20452032/170074284-72b28910-ba46-4172-9d7b-49c67958dbca.png">

<img width="1440" alt="Screen Shot 2022-05-24 at 11 35 57 AM" src="https://user-images.githubusercontent.com/20452032/170076352-bb05e521-19d5-4a25-a97f-61be4a4c7996.png">


## Set Environment Variables
- Change the value of each key as per your needs

export AWS_ACCESS_KEY_ID=<aws_access_key> <br>
export AWS_SECRET_ACCESS_KEY=<aws_secret_access_key> <br>
export GOOGLE_SHEET_ID="1G8U0pof44N1FkfRFFeydwd5p1_z5Jq_RFY33EJoVQf0" <br>
export SHEET_ALL_INSTANCES="EC2-All-Instances"<br>
export SHEET_OLD_INSTANCES="EC2-Old-Instances"<br>
export SHEET_ALL_EIPS="EIPs"<br>
export SHEET_ALL_ELBS="ELBs"<br>
export SHEET_ALL_BUCKETS="S3-All-Buckets"<br>
export SHEET_OLD_BUCKETS="S3-Old-Buckets"<br>
export SHEET_SUMMARY="Summary"<br>

<img width="1440" alt="Screen Shot 2022-05-24 at 10 43 00 AM" src="https://user-images.githubusercontent.com/20452032/170066197-f82d2022-34ab-4dd8-868d-8c23d7146f23.png">
<img width="1440" alt="Screen Shot 2022-05-24 at 10 44 34 AM" src="https://user-images.githubusercontent.com/20452032/170066229-7fb47077-2573-440c-a1b8-d1b8ebf12ef2.png">


## To run:
- Activate the python environment and run
```
  python ./main.py [arg]
```
> arg options: report, purge_instances, generate_ec2_deletion_summary, purge_vpcs

## To update dependencies:
1. pip install new packages as needed in development
1. $ `pip freeze > requirements.txt`
