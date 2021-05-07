"""
    Module to help estimate resource
    costs using AWS Pricing api
"""

import json
import boto3
from math import ceil
from datetime import datetime, timezone

def _elb_operation_filter_map(elb_type):
    """ returns operation filter for ELB """
    if elb_type == 'application':
        return 'LoadBalancing:Application'
    elif elb_type == 'network':
        return 'LoadBalancing:Network'
    else:
        return 'LoadBalancing'

def _ec2_usage_filter_map(instance_type):
    """ returns usageType filter for EC2
    """
    return {
        'us-east-1': 'BoxUsage:{}'.format(instance_type),
        'us-east-2': 'USE2-BoxUsage:{}'.format(instance_type),
        'us-west-1': 'USW1-BoxUsage:{}'.format(instance_type),
        'us-west-2': 'USW2-BoxUsage:{}'.format(instance_type),
        'eu-central-1': 'EUC1-BoxUsage:{}'.format(instance_type),
        'eu-west-1': 'EUW1-BoxUsage:{}'.format(instance_type),
        'eu-west-2': 'EUW2-BoxUsage:{}'.format(instance_type)
    }

def _region_filter_map():
    """ returns pricing query filter for region field
    """
    return {
        'us-east-1': 'US East (N. Virginia)',
        'us-east-2': 'US East (Ohio)',
        'us-west-1': 'US West (N. California)',
        'us-west-2': 'US West (Oregon)',
        'eu-central-1': 'EU (Frankfurt)',
        'eu-west-1': 'EU (Ireland)',
        'eu-west-2': 'EU (London)',
    }

def _ec2_pricing_filters(instance_type, region_code):
    """ returns a set of filters to match pricing info
        in specific region for given type  of instance
    """
    return [
        {
            'Field': 'operatingSystem',
            'Type': 'TERM_MATCH',
            'Value': 'Linux',
        },
        {
            'Field': 'preInstalledSw',
            'Type': 'TERM_MATCH',
            'Value': 'NA',
        },
        {
            'Field': 'instanceType',
            'Type': 'TERM_MATCH',
            'Value': instance_type
        },
        {
            'Field': 'location',
            'Type': 'TERM_MATCH',
            'Value': _region_filter_map()[region_code]
        },
        {
            'Field': 'usageType',
            'Type': 'TERM_MATCH',
            'Value': _ec2_usage_filter_map(instance_type)[region_code]
        },
        {
            'Field': 'tenancy',
            'Type': 'TERM_MATCH',
            'Value': 'shared'
        }
    ]

def _elb_pricing_filters(elb_type, region_code):
    """ returns a set of filters to match pricing info
        of Elastic Load Balancers in given region 
    """
    return [
        {
            'Field': 'location',
            'Type': 'TERM_MATCH',
            'Value': _region_filter_map()[region_code]
        },
        {
            'Field': 'operation',
            'Type': 'TERM_MATCH',
            'Value': _elb_operation_filter_map(elb_type)
        }
    ]

# store pricing info in cache
ec2_pricing_cache = {}
elb_pricing_cache = {}

def _get_price(service_code, filters):
    """ generic pricing info query builder
    """
    client = boto3.client('pricing')
    response = client.get_products(ServiceCode=service_code, Filters=filters, MaxResults=1)
    pricing_info = json.loads(response['PriceList'][0])['terms']['OnDemand']
    pricing_dimensions = pricing_info[list(pricing_info.keys())[0]]['priceDimensions']
    return float(pricing_dimensions[list(pricing_dimensions.keys())[0]]['pricePerUnit']['USD'])

def get_price_for_instance(instance_type, region_code):
    """ queries AWS pricing api to get pricing info for given instance
    """
    if instance_type in ec2_pricing_cache:
        if region_code in ec2_pricing_cache[instance_type]:
            return ec2_pricing_cache[instance_type][region_code]
    query_filters = _ec2_pricing_filters(instance_type, region_code)
    price_per_hour = _get_price('AmazonEC2', query_filters)
    if instance_type not in ec2_pricing_cache:
        ec2_pricing_cache[instance_type] = {}
    ec2_pricing_cache[instance_type][region_code] = price_per_hour
    return price_per_hour

def get_price_for_elb(elb_type, region_code):
    """ queries AWS pricing api to get pricing info for given elb
    """
    if elb_type in elb_pricing_cache:
        if region_code in elb_pricing_cache[elb_type]:
            return elb_pricing_cache[elb_type][region_code]
    query_filters = _elb_pricing_filters(elb_type, region_code)
    price_per_hour = _get_price('AWSELB', query_filters)
    if elb_type not in elb_pricing_cache:
        elb_pricing_cache[elb_type] = {}
    elb_pricing_cache[elb_type][region_code] = price_per_hour
    return price_per_hour

def _calculate_bill(launch_time, price_per_hour):
    utc_launch_time = launch_time.astimezone(timezone.utc)
    utc_now = datetime.now(tz=timezone.utc)
    total_bill = price_per_hour * ceil(float((utc_now - utc_launch_time).total_seconds()/3600))
    price_per_day = ceil(price_per_hour * 24)
    return total_bill, price_per_day

def calculate_bill_for_instance(instance_type, region_code, launch_time):
    """ calculates cost-to-date for a given EC2 instance using pricing info
    """
    price_per_hour = get_price_for_instance(instance_type, region_code)
    total_bill, price_per_day = _calculate_bill(launch_time, price_per_hour)
    return (price_per_hour, price_per_day, total_bill)

def calculate_bill_for_elb(elb_type, region_code, launch_time):
    """ calculates cost-to-date for a given ELB 
    """
    price_per_hour = get_price_for_elb(elb_type, region_code)
    total_bill, price_per_day = _calculate_bill(launch_time, price_per_hour)
    return (price_per_hour, price_per_day, total_bill)