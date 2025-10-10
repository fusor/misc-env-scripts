import logging
import os
import re
from datetime import datetime, timedelta

import pytz

from cloudformation import delete_stacks
from ec2 import get_all_instances, reformat_instance_data, \
    get_all_eips, reformat_eips_data, get_all_unused_volumes, \
    delete_volume, delete_eip, terminate_instance, EC2_KEYS
from elbs import get_all_elbs, reformat_elbs_data, delete_classic_elb
from emailer import Emailer
from s3 import get_all_buckets, reformat_buckets_data, delete_bucket
from sheet import GoogleSheetEditor
from vpc import get_all_vpcs, delete_orphan_vpcs

# number of days to qualify an instance as old
OLD_INSTANCE_THRESHOLD = 30

# number of days to qualify a bucket as old
OLD_BUCKETS_THRESHOLD = 60

def prepare_old_instances_data(all_instances_sheet, old_instances_sheet, tdelta=timedelta(days=0)):
    instances = all_instances_sheet.read_spreadsheet()
    existing_old_instances = old_instances_sheet.read_spreadsheet(indexField='InstanceId')
    old_instances = []
    for instance in instances:
        launch_time = datetime.strptime(instance['LaunchTime'], "%m/%d/%Y")
        now = datetime.utcnow() + tdelta
        if (now - launch_time).days > OLD_INSTANCE_THRESHOLD:
            instance['Saved'] = existing_old_instances.get(instance['InstanceId'], {}).get('Saved', '')
            instance['Notes'] = existing_old_instances.get(instance['InstanceId'], {}).get('Notes', '')
            old_instances.append(instance)
    if not old_instances:
        dummy_old_instance = {}
        for key in EC2_KEYS:
            split_keys = key.split('.')
            if len(split_keys) == 1:
                dummy_old_instance[key] = ''
            else:
                dummy_old_instance[split_keys[-1]] = ''
        dummy_old_instance['TotalBill'] = ''
        dummy_old_instance['Cost Per Day'] = ''
        dummy_old_instance['Saved'] = ''
        dummy_old_instance['Notes'] = ''
        return [dummy_old_instance]
    return old_instances

def prepare_old_s3_buckets_data(all_s3_buckets_sheet, old_s3_buckets_sheet):
    all_buckets = all_s3_buckets_sheet.read_spreadsheet()
    existin_old_buckets = old_s3_buckets_sheet.read_spreadsheet(indexField='Name')
    old_buckets = []
    for bucket in all_buckets:
        launch_time = datetime.strptime(bucket['CreationDate'], "%m/%d/%Y")
        now = datetime.utcnow()
        if (now - launch_time).days > OLD_BUCKETS_THRESHOLD:
            bucket['Saved'] = existin_old_buckets.get(bucket['Name'], {}).get('Saved', '')
            old_buckets.append(bucket)
    return old_buckets

def terminate_instances(old_instances_sheet, all_instances_sheet):
    old_instances = prepare_old_instances_data(all_instances_sheet, old_instances_sheet, timedelta(days=-4))
    instance_ids = []
    deleted_instances = 0
    for inst in old_instances:
        if 'save' not in inst['Saved'].lower():
            instance_id = inst['InstanceId']
            instance_region = re.sub(r'(\w+)-(\w+)-(\d)\w+', r"\g<1>-\g<2>-\g<3>", inst["AvailabilityZone"])
            instance_ids.append([instance_id, instance_region])
    for inst in instance_ids:
        response = terminate_instance(inst[0], inst[1])
        if response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500) == 200:
            deleted_instances += 1
    return deleted_instances       

def delete_unused_volumes():
    deleted_vols = 0
    vols = get_all_unused_volumes()
    for vol in vols:
        response = delete_volume(vol['VolumeId'], vol['Region'])
        if response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500) == 200:
            deleted_vols += 1
    return deleted_vols

def delete_unassigned_elbs(elbs):
    deleted_elbs = 0
    for elb in elbs:
        if elb['Instances'] == 'Unassigned' and elb['Type'] == 'classic':
            response = delete_classic_elb(elb['LoadBalancerName'], elb['Region'])
            if response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500) == 200:
                deleted_elbs += 1 
    return deleted_elbs

def delete_unassigned_eips(eips):
    deleted_eips = 0
    for eip in eips:
        if 'InstanceId' not in eip or eip['InstanceId'] == '':
            response = delete_eip(eip)
            if response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500) == 200:
                deleted_eips += 1 
    return deleted_eips

def delete_vpcs():
    vpcs = get_all_vpcs()
    deleted_vpcs = delete_orphan_vpcs(vpcs)
    return deleted_vpcs

def get_old_instances_email_summary(oldInstancesSheet, allInstancesSheet, summarySheet):
    sheet_link = os.environ['SHEET_LINK']
    old_instances = prepare_old_instances_data(allInstancesSheet, oldInstancesSheet)
    if summarySheet is not None:
        try:
            total_ec2_deleted = summarySheet.read_custom('J1', 'J1')[0][0]
        except:
            total_ec2_deleted = None
    message = """
All,<br>
<br>            
This is a reminder to let you know that the AWS cleanup automation script will terminate some of the long running EC2 instances.<br>
<br>
You can save your instances from automatic deletion by writing 'Save' in the 'Saved' column in 'EC2-Old-Instances' spreadsheet below:
<br>
<br>
<a href="{}">{}</a>
<br>
<br>
Next cleanup is scheduled on <b>{}</b>.
<br><br>
Here's the summary of instances scheduled for termination:
<br><br>
{}
<br><br>
Thank you.<br>
        """
    scheduled = (datetime.utcnow() + timedelta(days=4)).strftime("%a, %b %d, %y")
    unique_owners = {}
    orphan_instances = []
    for inst in old_instances:
        if 'save' in inst['Saved'].lower():
            continue
        owner = inst.get('owner', 'OwnerNotFound')
        if owner != 'OwnerNotFound' and owner != "":
            guid = inst.get('guid', '')
            if owner in unique_owners:
                unique_owners[owner]['count'] += 1
                if guid not in unique_owners[owner]['guids']:
                    unique_owners[owner]['guids'].append(guid)
            else:
                unique_owners[owner] = {'count': 1, 'guids': [guid]}
        else:
            orphan_instances.append(inst)
    if len(unique_owners.keys()) == 0 and len(orphan_instances) == 0:
        return None
    summary_email = ""
    for k, v in unique_owners.items():
        summary_email += "- {} unsaved instances owned by {} associated with GUIDs <b>{}</b><br>"\
                                    .format(v.get('count'), k, v.get('guids'))
    if len(orphan_instances) > 0:
        summary_email += "<br><br> Following instances could not be associated with owners:<br>"
        for inst in orphan_instances:
            summary_email += "- Name: {}, Instance Id : {}, Region : {}<br>".format(inst.get('Name', ''), inst['InstanceId'], inst['AvailabilityZone'])
    if total_ec2_deleted is not None:
        summary_email += "<br><br> Total EC2 instances deleted so far: <b>{}</b><br>".format(str(total_ec2_deleted))
    return message.format(sheet_link, sheet_link, scheduled, summary_email)


def start(argument):
    logging.basicConfig(
        filename='./cleaner.log',
        format='[%(levelname)s] [%(name)s] [%(asctime)s] %(message)s',
        level=logging.INFO
    )
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)
    logging.getLogger('googleapiclient').setLevel(logging.ERROR)

    sheet_id = os.environ['GOOGLE_SHEET_ID']
    allInstancesSheetName = os.environ['SHEET_ALL_INSTANCES']
    oldInstancesSheetName = os.environ['SHEET_OLD_INSTANCES']
    allEipsSheetName = os.environ['SHEET_ALL_EIPS']
    allElbsSheetName = os.environ['SHEET_ALL_ELBS']
    allS3SheetName = os.environ['SHEET_ALL_BUCKETS']
    oldS3SheetName = os.environ['SHEET_OLD_BUCKETS']
    summarySheetName = os.environ['SHEET_SUMMARY']

    allInstancesSheet = GoogleSheetEditor(sheet_id, allInstancesSheetName)
    oldInstancesSheet = GoogleSheetEditor(sheet_id, oldInstancesSheetName)
    allEipsSheet = GoogleSheetEditor(sheet_id, allEipsSheetName)
    allElbsSheet = GoogleSheetEditor(sheet_id, allElbsSheetName)
    allS3Sheet = GoogleSheetEditor(sheet_id, allS3SheetName)
    oldS3Sheet = GoogleSheetEditor(sheet_id, oldS3SheetName)
    summarySheet = GoogleSheetEditor(sheet_id, summarySheetName)

    summaryRow = {
        'Date': '',
        'EC2 Daily Cost': '',
        'ELBs Daily Cost': '',
        'ELBs': '',
        'Volumes': '',
        'VPC Cleanup': '',
        'EC2 Cleanup': '',
    }
    now = datetime.now(pytz.timezone('US/Eastern')).strftime("%H:%M:%S %B %d, %Y")
    summaryRow['Date'] = now

    skip_summary = False

    if argument == 'report':
        # update all instances sheet
        instances = get_all_instances()
        instances = reformat_instance_data(instances)
        instances_daily_bill = 0.0
        for instance in instances:
            if instance['Cost Per Day']:
                instances_daily_bill += float(re.sub(r'\$', '', instance['Cost Per Day']))
        summaryRow['EC2 Daily Cost'] = "${}".format(str(instances_daily_bill))
        print(allInstancesSheet.save_data_to_sheet(instances))
        # update old instance sheet
        instances = prepare_old_instances_data(allInstancesSheet, oldInstancesSheet)
        print(oldInstancesSheet.save_data_to_sheet(instances))

        # update eips sheet
        eips = get_all_eips()
        eips = reformat_eips_data(eips)
        print(allEipsSheet.save_data_to_sheet(eips))

        # update elbs sheet
        elbs = get_all_elbs()
        elbs = reformat_elbs_data(elbs)
        numberOfElbsDeleted = delete_unassigned_elbs(elbs)
        summaryRow['ELBs'] = 'Deleted {} elbs'.format(numberOfElbsDeleted)
        elbs_daily_bill = 0.0
        for elb in elbs:
            elbs_daily_bill += float(re.sub(r'\$', '', elb['CostPerDay']))
        summaryRow['ELBs Daily Cost'] = "${}".format(str(elbs_daily_bill))
        print(allElbsSheet.save_data_to_sheet(elbs))

        # delete old volumes
        numberOfVolumesDeleted = delete_unused_volumes()
        summaryRow['Volumes'] = 'Deleted {} volumes'.format(numberOfVolumesDeleted)

        # update all buckets sheet
        buckets = get_all_buckets()
        buckets = reformat_buckets_data(buckets)
        print(allS3Sheet.save_data_to_sheet(buckets))
        # update old buckets sheet
        buckets = prepare_old_s3_buckets_data(allS3Sheet, oldS3Sheet)
        print(oldS3Sheet.save_data_to_sheet(buckets))

    elif argument == 'purge_instances':
        numberOfInstancesDeleted = terminate_instances(oldInstancesSheet, allInstancesSheet)
        summaryRow['EC2 Cleanup'] = 'Deleted {} instances'.format(numberOfInstancesDeleted)
        delete_stacks()

    elif argument == 'purge_s3':
        buckets = oldS3Sheet.read_spreadsheet()
        for bucket in buckets:
            name = bucket.get('Name', '')
            saved = bucket.get('Saved', '')
            if name != '' and saved not in ["Saved", "Save", "save"]:
                delete_bucket(bucket=bucket.get('Name'))

    elif argument == 'generate_ec2_deletion_summary':
        summaryEmail = get_old_instances_email_summary(oldInstancesSheet, allInstancesSheet, summarySheet)
        print("SummaryEmail", summaryEmail)
        if summaryEmail is not None:
            smtp_addr = os.environ['SMTP_ADDR']
            smtp_username = os.environ['SMTP_USERNAME']
            smtp_password = os.environ['SMTP_PASSWORD']
            smtp_sender = os.environ['SMTP_SENDER']
            smtp_receivers = os.environ['SMTP_RECEIVERS'].split(',')
            emailer = Emailer(smtp_addr, smtp_username, smtp_password)
            emailer.send_email(smtp_sender, smtp_receivers, 'AWS Cleanup Notification', summaryEmail)
        skip_summary = True

    elif argument == 'purge_vpcs':
        numberOfVpcsDeleted = delete_vpcs()
        summaryRow['VPC Cleanup'] = 'Deleted {} vpcs'.format(numberOfVpcsDeleted)
        numberOfEipsDeleted = delete_unassigned_eips(get_all_eips())
        summaryRow['EC2 Cleanup'] = 'Deleted {} eips'.format(numberOfEipsDeleted)
    else:
        pass

    if not skip_summary:
        summarySheet.append_data_to_sheet([summaryRow])

