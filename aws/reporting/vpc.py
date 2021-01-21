import sys
import boto3
import logging
import boto3.session
from time import sleep
from common import get_all_regions

logger = logging.getLogger(__name__)

def get_all_vpcs():
    vpcs = {}
    for region in get_all_regions():
        if vpcs.get(region, None) == None:
            vpcs[region] = []
        vpcs_in_region = boto3.client('ec2', region_name=region).describe_vpcs()['Vpcs']
        vpcs[region].extend(vpcs_in_region)
    return vpcs

def _is_orphan(vpc_res):
    """ tries to identify whether vpc is orphan
        criteria of orphan includes:
            1. no instances present in the VPC
    """
    for instance in vpc_res.instances.all():
        return False
    return True

def delete_orphan_vpcs(vpcs):
    """ identifies orphan vpcs and deletes them
        vpcs (dict): each item in the list is a map of
                        region -> [vpcs in the region]
    """
    deleted_vpcs = 0
    for region in vpcs.keys():
        session = boto3.session.Session(region_name=region)
        client = session.resource('ec2')
        meta_client = client.meta.client
        for vpc in vpcs[region]:
            try:
                vpc_res = client.Vpc(vpc['VpcId'])
            except Exception as e:
                logger.info("{} Error finding VPC {}".format(region, vpc['VpcId']))
                continue
            try:
                if not _is_orphan(vpc_res):
                    logger.info("{} Skipping non-orphan vpc {}".format(region, vpc_res.id))
                    continue
                if vpc_res.is_default:
                    logger.info("{} Skipping default vpc {}".format(region, vpc_res.id))
                    continue
            except Exception as e:
                continue
            logger.info("{} Attempting to delete vpc {}".format(region, vpc_res.id))
            # detach default dhcp_options if associated with the vpc
            dhcp_options_default = client.DhcpOptions('default')
            if dhcp_options_default:
                dhcp_options_default.associate_with_vpc(VpcId=vpc_res.id)
            # delete load balancers
            for elb in session.client('elbv2').describe_load_balancers()['LoadBalancers']:
                if elb['VpcId'] == vpc_res.id:
                    try:
                        logger.info("{} Attempting to delete elb {}".format(region, elb['LoadBalancerArn']))
                        session.client('elbv2').delete_load_balancer(LoadBalancerArn=elb['LoadBalancerArn'])
                    except Exception as e:
                        logger.info("{} Error deleting elb {}".format(region, elb['LoadBalancerArn']))
                        logger.error(str(e))
            sleep(10)
            # delete network interfaces
            for eni in vpc_res.network_interfaces.all():
                try:
                    logger.info("{} Attempting to delete eni {}".format(region, eni.id))
                    eni.detach()
                    sleep(5)
                    eni.delete()
                except Exception as e:
                    logger.info("{} Error deleting eni {}".format(region, eni.id))
                    logger.error(str(e))
            # delete internet gateways
            for ig in vpc_res.internet_gateways.all():
                try:
                    logger.info("{} Attempting to delete ig {}".format(region, ig.id))
                    vpc_res.detach_internet_gateway(InternetGatewayId=ig.id)
                    sleep(5)
                    ig.delete()
                except Exception as e:
                    logger.info("{} Error deleting ig {}".format(region, ig.id))
                    logger.error(str(e))
            # delete route tables
            for rt in vpc_res.route_tables.all():
                for rta in rt.associations:
                    try:
                        if not rta.main:
                            logger.info("{} Attempting to delete rt {}".format(region, rta.id))
                            rta.delete()
                    except Exception as e:
                        logger.info("{} Error deleting rt {}".format(region, rta.id))
                        logger.error(str(e))
                try:
                    rt.delete()
                except Exception as e:
                    logger.info("{} Error deleting rt {}".format(region, rta.id))
                    logger.error(str(e))
            # delete endpoints
            for eip in meta_client.describe_vpc_endpoints(Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_res.id]
                    }
                ])['VpcEndpoints']:
                try:
                    logger.info("{} Attempting to delete endpoint {}".format(region, eip['VpcEndpointId']))
                    meta_client.delete_vpc_endpoints(VpcEndpointIds=[eip['VpcEndpointId']])
                except Exception as e:
                    logger.info("{} Error deleting endpoint {}".format(region, eip['VpcEndpointId']))
                    logger.error(str(e))
            # delete ingress / egress rules
            for sg in vpc_res.security_groups.all():
                try:
                    if sg.group_name != 'default':
                        logger.info("{} Attempting to revoke ingress from group {}".format(region, sg.id))
                        sg.revoke_ingress(IpPermissions=sg.ip_permissions)
                        sleep(3)
                        logger.info("{} Attempting to revoke egress from group {}".format(region, sg.id))
                        sg.revoke_egress(IpPermissions=sg.ip_permissions_egress)
                except Exception as e:
                    logger.info("{} Error revoking ingress / egress from group {}".format(region, sg.id))
                    logger.error(str(e))
            # delete security groups
            for sg in vpc_res.security_groups.all():
                try:
                    if sg.group_name != 'default':
                        logger.info("{} Attempting to delete sec group {}".format(region, sg.id))
                        sg.delete()
                except Exception as e:
                    logger.info("{} Failed deleting sec group {}".format(region, sg.id))
                    logger.error(str(e))
            # delete peering connections
            for pconn in meta_client.describe_vpc_peering_connections(Filters=[
                    {
                        'Name': 'requester-vpc-info.vpc-id',
                        'Values': [vpc_res.id]
                    }
                ])['VpcPeeringConnections']:
                try:
                    logger.info("{} Attempting to delete peering conn {}".format(region, pconn['VpcPeeringConnectionId']))
                    client.VpcPeeringConnection(pconn['VpcPeeringConnectionId']).delete()
                except Exception as e:
                    logger.info("{} Error deleting peering conn {}".format(region, pconn['VpcPeeringConnectionId']))
                    logger.error(str(e))
            # delete network acls
            for acl in vpc_res.network_acls.all():
                if not acl.is_default:
                    try:
                        logger.info("{} Attempting to delete acl {}".format(region, acl.id))
                        acl.delete()
                    except Exception as e:
                        logger.info("{} Error deleting acl {}".format(region, acl.id))
                        logger.error(str(e))
            # delete network interfaces
            for subnet in vpc_res.subnets.all():
                for interface in subnet.network_interfaces.all():
                    try:
                        logger.info("{} Attempting to delete network iface {}".format(region, interface.id))
                        interface.delete()
                    except Exception as e:
                        logger.info("{} Error deleting network iface {}".format(region, interface.id))
                        logger.error(str(e))
                try:
                    logger.info("{} Attempting to delete subnet {}".format(region, subnet.id))
                    subnet.delete()
                except Exception as e:
                    logger.info("{} Error deleting subnet {}".format(region, subnet.id))
                    logger.error(str(e))
            # delete nat gateways
            for nat in meta_client.describe_nat_gateways(Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_res.id]
                    }
                ])['NatGateways']:
                try:
                    logger.info("{} Attempting to delete nat gateway {}".format(region, nat['NatGatewayId']))
                    meta_client.delete_nat_gateway(NatGatewayId=nat['NatGatewayId'])
                except Exception as e:
                    logger.info("{} Error deleting nat gateway {}".format(region, nat['NatGatewayId']))
                    logger.error(str(e))
            try:
                vpc_res.delete()
                deleted_vpcs += 1
            except Exception as e:
                logger.info("{} Error deleting vpc {}".format(region, vpc_res.id))
                logger.error(str(e))
    return deleted_vpcs
