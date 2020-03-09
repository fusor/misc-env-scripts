import boto3    
import pprint 


# Instance info
#   InstanceId
#   InstanceType
#   LaunchTime
#   IamInstanceProfile['Arn']
# Tags': [{u'Key': 'Name', u'Value': 'dwhatley-1-mvqqq-master-1'}
# u'Value': 'owned'},
#                           {u'Key': 'owner',
#                            u'Value': 'pgaikwad@redhat.com'},
#                           {u'Key': 'Name',
#                            u'Value': 'cluster-pranav-sqzff-worker-us-east-1a-nfbdh'},
#                           {u'Key': 'guid', u'Value': 'pranav'},
# SecurityGroups
#   GroupName
#
# Region
#  u'Placement': {u'AvailabilityZone': 'us-east-1f',


def get_all_region_names(client):
    regions = []
    response = client.describe_regions()
    for r in response['Regions']:
        regions.append(r['RegionName'])
    return regions

def get_all_instances_in_regions(regions):
    all_instances = []
    for r in regions:
        instances_in_region = get_all_instances_per_region(r)
        all_instances.extend(instances_in_region)
    return all_instances

def get_all_instances_per_region(region):
    instances = []
    ec2client = boto3.client('ec2',region_name=region)
    response = ec2client.describe_instances()
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            if instance['State']['Name'] == 'running':
                #pprint.pprint(instance)
                instances.append(instance)
    return instances

def reformat_instance_data(raw_instances):
    instances = {}
    for r in raw_instances:
        inst = {}
        who = {}
        inst['InstanceId'] = r['InstanceId']
        inst['InstanceType'] = r['InstanceType']
        inst['LaunchTime'] = r['LaunchTime']
        if r.has_key("IamInstanceProfile"):
            if r["IamInstanceProfile"].has_key("Arn"):
                who['Arn'] = r['IamInstanceProfile']['Arn']
        for entry in r["Tags"]:
            for k in ["owner", "Name", "guid"]:
                if k in entry["Key"]:
                    who[k] = entry["Value"]
        inst['who'] = who 
        instances[inst['InstanceId']] = inst
    return instances

def cmp_LaunchTime(a, b):
    if a["LaunchTime"] > b["LaunchTime"]:
        return 1
    elif a["LaunchTime"] == b["LaunchTime"]:
        return 0
    else:
        return -1


ec2client = boto3.client('ec2')
regions = get_all_region_names(ec2client)
#regions = ['us-east-1']
for region in regions:
    print "Processing %s" % (region)
    instances = get_all_instances_in_regions([region])
    instances.sort(cmp_LaunchTime)
    print "%s:\t found %s instances" % (region, len(instances))
    outFile = open("%s.txt" % region, 'w')
    pp = pprint.PrettyPrinter(indent=2, stream=outFile)
    pp.pprint(instances)   
    #pprint.pprint(instances)
# Sort by LaunchTime
#data = reformat_instance_data(instances)

#pprint.pprint(data)
#pprint.pprint(instances)
#pprint.pprint(regions) 
print "%s instances found" % (len(instances))