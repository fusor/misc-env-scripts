import boto3
import logging
from common import get_all_regions

DELETEABLE_STATUS = ["CREATE_FAILED", "DELETE_FAILED"]

AWS_RESOURCE_TYPE_EC2_INSTANCE = "AWS::EC2::Instance"

AWS_EKS_MANAGED_TAGS = ["alpha.eksctl.io/cluster-name"]

logger = logging.getLogger(__name__)

def default_filter(client, stacks):
    filtered_stacks = []
    for stack in stacks:
        stackName = stack.get("StackName", "")
        if stackName != "":
            is_eks_managed = False
            for tag in stack.get('Tags', []):
                if tag.get('Key', '') in AWS_EKS_MANAGED_TAGS:
                    is_eks_managed = True
                    logger.info("{} Found EKS managed stack {}".format(client.meta.region_name, stackName))
            if not is_eks_managed:
                if stack.get('StackStatus', '') in DELETEABLE_STATUS:
                    filtered_stacks.append(stack)
                    logger.info("{} Found stack with deleteable status {}".format(client.meta.region_name, stackName))
                elif not does_cf_template_have_ec2_instances(client, stackName):
                    filtered_stacks.append(stack)
                    logger.info("{} Found stack without instances {}".format(client.meta.region_name, stackName))
    return filtered_stacks

def no_filter(client, stacks):
    return stacks

def get_deleteable_cf_templates(client, filter_func=default_filter):
    deleteable_stacks = []
    response = client.describe_stacks()
    return filter_func(client, response.get('Stacks', []))

def does_cf_template_have_ec2_instances(client, stack_name: str):
    for resource in client.describe_stack_resources(StackName=stack_name)['StackResources']:
        if resource.get('ResourceType', '') == AWS_RESOURCE_TYPE_EC2_INSTANCE:
            return True
    return False

def delete_stacks(dry_run = False, filter_func=default_filter):
    for region in get_all_regions():
        client = boto3.client('cloudformation', region_name=region)
        stacks = get_deleteable_cf_templates(client, filter_func=filter_func)
        for stack in stacks:
            stackName = stack.get("StackName", "")
            if stackName != "":
                try:
                    logger.info("{} Attempting to delete stack {}".format(region, stackName))
                    if not dry_run:
                        client.delete_stack(StackName=stackName)
                    logger.info("{} Deleted stack {}".format(region, stackName))
                except:
                    logger.info("{} Failed deleting stack {}".format(region, stackName))

if __name__ == "__main__":
    import sys
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    delete_stacks(filter_func=no_filter)