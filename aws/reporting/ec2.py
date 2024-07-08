import re
import boto3
import logging
from pricing import calculate_bill_for_instance
from common import reformat_data, get_all_regions

logger = logging.getLogger(__name__)

EC2_KEYS = [
    'InstanceId',
    'InstanceType',
    'Placement.AvailabilityZone',
    'LaunchTime',
    'IamInstanceProfile.Arn',
    'Tags.owner',
    'Tags.Name',
    'Tags.guid'
]

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
                logger.info("{} Found instance {}".format(region, instance['InstanceId']))
    return instances

def reformat_instance_data(raw_instances):
    formatted_instances = reformat_data(raw_instances, EC2_KEYS)
    for inst in formatted_instances:
        region = re.sub(r'(\w+)-(\w+)-(\d)\w+', r"\g<1>-\g<2>-\g<3>", inst["AvailabilityZone"])
        instance_type = inst['InstanceType']
        launch_time = inst['LaunchTime']
        try:
            inst['TotalBill'] = "${}".format(calculate_bill_for_instance(instance_type, region, launch_time)[2])
        except:
            inst['TotalBill'] = "$0"
        try:
            inst['Cost Per Day'] = "${}".format(calculate_bill_for_instance(instance_type, region, launch_time)[1])
        except:
            inst['Cost Per Day'] = "$0"
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
        'AllocationId',
        'NetworkBorderGroup',
        'InstanceId',
        'Tags.guid',
        'Tags.owner'
    ]
    eips = reformat_data(raw_eips, keys)
    for eip in eips:
        if 'NetworkBorderGroup' in eip:
            eip['Region'] = eip['NetworkBorderGroup']
            del eip['NetworkBorderGroup']
    return eips

def get_all_unused_volumes():
    all_volumes = []
    for region in get_all_regions():
        vols = []
        client = boto3.client('ec2', region_name=region)
        filters = [
            {
                'Name': 'status',
                'Values': ['available', 'error']
            }
        ]
        for vol in client.describe_volumes(Filters=filters)['Volumes']:
            vol['Region'] = region
            vols.append(vol)
            logger.info("{} Found unused vol {}".format(region, vol))
        all_volumes.extend(vols)
    return all_volumes

def delete_volume(volume_id, region):
    response = {}
    try:
        logger.info("{} Attempting to delete vol {}".format(region, volume_id))
        response = boto3.client('ec2', region_name=region).delete_volume(VolumeId=volume_id)
    except Exception as e:
        logger.info("{} Error deleting vol {}".format(region, volume_id))
        logger.error(str(e))
    return response

def delete_eip(eip):
    response = {}
    region = eip.get('NetworkBorderGroup', '')
    try:
        logger.info("{} Attempting to delete eip {}".format(region, eip['AllocationId']))
        if region != '':
            ec2Client = boto3.client('ec2', region_name=region)
        else:
            ec2Client = boto3.client('ec2')
        response = ec2Client.release_address(AllocationId=eip['AllocationId'])
    except Exception as e:
        logger.info("{} Error deleting eip {}".format(region, eip['AllocationId']))
        logger.error(str(e))
    return response

def terminate_instance(instance_id, region):
    response = {}
    try:
        logger.info("{} Attempting to terminate instance {}".format(region, instance_id))
        response = boto3.client('ec2', region_name=region).terminate_instances(InstanceIds=[instance_id])
    except Exception as e:
        logger.info("{} Error terminating instance {}".format(region, instance_id))
        logger.error(str(e))
    return response

