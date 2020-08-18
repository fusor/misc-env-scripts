import re
import boto3
from pricing import calculate_bill_for_instance
from common import reformat_data, get_all_regions

EC2_PRICING_API_URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json"
EC2_PRICING_INFO_FILE = "./ec2_pricing.json"

def get_all_instances():
    all_instances = []
    for r in get_all_regions():
        instances_in_region = get_instances_per_region(r)
        all_instances.extend(instances_in_region)
    return all_instances

def get_instances_per_region(region):
    instances = []
    ec2client = boto3.client('ec2',region_name=region)
    response = ec2client.describe_instances()
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            if instance['State']['Name'] == 'running':
                instances.append(instance)
    return instances

def reformat_instance_data(raw_instances):
    keys = [
        'InstanceId',
        'InstanceType',
        'Placement.AvailabilityZone',
        'LaunchTime',
        'IamInstanceProfile.Arn',
        'Tags.owner',
        'Tags.Name',
        'Tags.guid'
    ]
    formatted_instances = reformat_data(raw_instances, keys)
    for inst in formatted_instances:
        region = re.sub(r'(\w+)-(\w+)-(\d)\w+', "\g<1>-\g<2>-\g<3>", inst["AvailabilityZone"])
        instance_type = inst['InstanceType']
        launch_time = inst['LaunchTime']
        inst['TotalBill'] = "${}".format(calculate_bill_for_instance(instance_type, region, launch_time)[2])
        inst['Cost Per Day'] = "${}".format(calculate_bill_for_instance(instance_type, region, launch_time)[1])
    return formatted_instances

def get_all_eips():
    all_eips = []
    for region in get_all_regions():
        client = boto3.client('ec2', region_name=region)
        response = client.describe_addresses()
        if response['Addresses']:
            all_eips.extend(response['Addresses'])
    return all_eips

def reformat_eips_data(raw_eips):
    keys = [
        'Tags.Name',
        'PublicIp',
        'NetworkBorderGroup',
        'InstanceId',
        'Tags.guid',
        'Tags.owner'
    ]
    return reformat_data(raw_eips, keys)

def terminate_instances(instance_ids):
    client = boto3.client('ec2')
    return client.terminate_instances(InstanceIds=instance_ids)
