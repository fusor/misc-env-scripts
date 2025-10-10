import re
import boto3
import logging
from pricing import calculate_bill_for_elb
from common import reformat_data, get_all_regions

logger = logging.getLogger(__name__)

def get_all_elbs():
    elbs = []
    for region in get_all_regions():
        # classic elbs
        client = boto3.client('elb', region_name=region)
        response = client.describe_load_balancers()
        elbs.extend(response['LoadBalancerDescriptions'])
        # application + network
        client = boto3.client('elbv2', region_name=region)
        response = client.describe_load_balancers()
        elbs.extend(response['LoadBalancers'])
    return elbs

def reformat_elbs_data(elbs):
    keys = [
        'LoadBalancerName',
        'AvailabilityZones',
        'VPCId',
        'CreatedTime',
        'Instances',
        'Type',
        'State.Code'
    ]
    elbs = reformat_data(elbs, keys)
    for elb in elbs:
        if elb['Type'] == '':
            elb['Type'] = 'classic'
            if len(elb.get('Instances', [])) > 0:
                elb['Instances'] = 'Assigned'
            else: 
                elb['Instances'] = 'Unassigned'
        if elb['Type'] == 'network':
            elb['Status'] = elb['Code']
        if len(elb.get('AvailabilityZones', [])) > 0:
            if isinstance(elb['AvailabilityZones'][0], dict):
                az = elb['AvailabilityZones'][0]['ZoneName']
            else:
                az = elb['AvailabilityZones'][0]
            elb['Region'] = re.sub(r'(\w+)-(\w+)-(\d)\w+', r"\g<1>-\g<2>-\g<3>", az)
        elb['TotalBill'] = "${}".format(calculate_bill_for_elb(elb['Type'], elb['Region'], elb['CreatedTime'])[2])
        elb['CostPerDay'] = "${}".format(calculate_bill_for_elb(elb['Type'], elb['Region'], elb['CreatedTime'])[1])
        if 'AvailabilityZones' in elb:
            del elb['AvailabilityZones']
        if 'Code' in elb:
            del elb['Code']
    return elbs

def delete_classic_elb(elb_name, region):
    response = {}
    try:
        logger.info("{} Attempting to delete elb {}".format(region, elb_name))
        response = boto3.client('elb', region_name=region).delete_load_balancer(LoadBalancerName=elb_name)
    except Exception as e:
        logger.info("{} Error deleting elb {}".format(region, elb_name))
        logger.error(str(e))
    return response

if __name__ == "__main__":
    import sys
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    for elb in reformat_elbs_data(get_all_elbs()):
        if elb.get("Region", "") != "" and elb.get("LoadBalancerName", "") != "":
            response = delete_classic_elb(elb['LoadBalancerName'], elb['Region'])
