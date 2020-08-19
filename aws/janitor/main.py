import os
from datetime import datetime
from sheet import GoogleSheetEditor
from ec2 import get_all_instances, reformat_instance_data,\
    get_all_eips, reformat_eips_data
from elbs import get_all_elbs, reformat_elbs_data
from common import save_to_file, load_from_file
from s3 import get_all_buckets, reformat_buckets_data

# number of days to qualify an instance as old
OLD_INSTANCE_THRESHOLD = 30

# number of days to qualify a bucket as old
OLD_BUCKETS_THRESHOLD = 60

def prepare_old_instances_data(all_instances_sheet, old_instances_sheet):
    instances = all_instances_sheet.read_spreadsheet()
    existing_old_instances = old_instances_sheet.read_spreadsheet(indexField='InstanceId')
    old_instances = []
    for instance in instances:
        launch_time = datetime.strptime(instance['LaunchTime'], "%m/%d/%Y")
        now = datetime.utcnow()
        if (now - launch_time).days > OLD_INSTANCE_THRESHOLD:
            instance['Saved'] = existing_old_instances.get(instance['InstanceId'], {}).get('Saved', '')
            instance['Notes'] = existing_old_instances.get(instance['InstanceId'], {}).get('Notes', '')
            old_instances.append(instance)
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

def terminate_instances(old_instances_sheet):
    old_instances = old_instances_sheet.read_spreadsheet()
    instance_ids = []
    for inst in old_instances:
        now = datetime.utcnow()
        if 'save' not in inst['Saved'].lower():
            instance_ids.append(inst['InstanceId'])
    return instance_ids       

if __name__ == "__main__":
    sheet_id = os.environ['GOOGLE_SHEET_ID']
    allInstancesSheetName = os.environ['SHEET_ALL_INSTANCES']
    oldInstancesSheetName = os.environ['SHEET_OLD_INSTANCES']
    allEipsSheetName = os.environ['SHEET_ALL_EIPS']
    allElbsSheetName = os.environ['SHEET_ALL_ELBS']
    allS3SheetName = os.environ['SHEET_ALL_BUCKETS']
    oldS3SheetName = os.environ['SHEET_OLD_BUCKETS']

    allInstancesSheet = GoogleSheetEditor(sheet_id, allInstancesSheetName)
    oldInstancesSheet = GoogleSheetEditor(sheet_id, oldInstancesSheetName)
    allEipsSheet = GoogleSheetEditor(sheet_id, allEipsSheetName)
    allElbsSheet = GoogleSheetEditor(sheet_id, allElbsSheetName)
    allS3Sheet = GoogleSheetEditor(sheet_id, allS3SheetName)
    oldS3Sheet = GoogleSheetEditor(sheet_id, oldS3SheetName)

    instances = get_all_instances()
    instances = reformat_instance_data(instances)
    print(allInstancesSheet.save_data_to_sheet(instances))
    instances = prepare_old_instances_data(allInstancesSheet, oldInstancesSheet)
    print(oldInstancesSheet.save_data_to_sheet(instances))

    eips = get_all_eips()
    eips = reformat_eips_data(eips)
    print(allEipsSheet.save_data_to_sheet(eips))

    elbs = get_all_elbs()
    elbs = reformat_elbs_data(elbs)
    print(allElbsSheet.save_data_to_sheet(elbs))

    buckets = get_all_buckets()
    buckets = reformat_buckets_data(buckets)
    print(allS3Sheet.save_data_to_sheet(buckets))
    buckets = prepare_old_s3_buckets_data(allS3Sheet, oldS3Sheet)
    print(oldS3Sheet.save_data_to_sheet(buckets))



