import json
import main


def lambda_handler(event, context):
    status_code = 200
    msg = "Success!"
    try:
        print('command', event['command'])
        main.start(event['command'])
    except Exception as e:
        status_code = 404
        msg = str(e)

    return {
        'statusCode': status_code,
        'body': json.dumps(msg)
    }


# Report every day 10 AM
# Every Monday 10 AM - Report(1) + EC2_deletion_summary -> purge_vpcs
# Every Friday - Purge Instances + Purge_VPCs
# Consolidate all policy in single json
# script creation of lambda function
