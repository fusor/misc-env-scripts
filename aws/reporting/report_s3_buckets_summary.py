#!/usr/bin/env python

import boto3
import common
from pytz import utc
from pprint import pprint
from operator import itemgetter
from datetime import datetime, timedelta

"""
    Goals : 
    - Prepare list of all S3 buckets in migration account 
    - Filter S3 buckets based on timestamp (old or not-old)
    - Report data to the accounting spreadsheet
    - Read spreadsheet for buckets that are marked as "Saved"
    - Apply tags to buckets that are marked as "Saved" in the spreadsheet

    Non-Goals : 
    - Delete buckets
    - Estimate costs
"""

# mark buckets older than 
# the below value as "OLD"
FILTER_BUCKET_DAYS = 60

# spreadsheet headers for list 
# of all S3 buckets found 
SPREADSHEET_S3_LABELS = [
    "Name",
    "Created",
    "Saved?"
]

# spreadsheet headers for list
# of S3 buckets marked as old 
SPREADSHEET_S3_LABELS_OLD = [
    "Name",
    "Created",
    "Saved?"
]

SPREADSHEET_ID = '1XOMu12uPJgtX_gN3mUTQu89kArzBft4edhbkXqlae5M'
S3_ALL_SHEET = 'S3-All-Buckets'
S3_OLD_SHEET = 'S3-Old-Buckets'

def _read_spreadsheet(sheet_client, sheet_id):
    existing_data = []
    result = sheet_client.values().get(
        spreadsheetId=SPREADSHEET_ID, range='%s!B3:Z'%sheet_id).execute()
    rows = result.get('values', [])
    for row in rows[2:]:
        existing_data.append([row[0], 
            datetime.strptime(row[1],'%B %d, %Y'), 
            True if (len(row) > 2 and row[2] == 'Save') else False])
    return existing_data

def _clear_spreadsheet(sheet_client, sheet_id):
    return sheet_client.values().clear(spreadsheetId=SPREADSHEET_ID, range='%s!B3:Z'%sheet_id).execute()

def _fill_spreadsheet(sheet_client, sheet_id, buckets):
    values = []
    for bucket in buckets:
        value = []
        value.append(bucket[0])
        value.append(bucket[1].strftime("%B %d, %Y"))
        if bucket[2]:
            value.append('Save')
        values.append(value)
    body = { 'values': values }
    print("Attempting to update sheet...")
    result = sheet_client.values().update(
        spreadsheetId=SPREADSHEET_ID, range='%s!B3:Z'%sheet_id,
        valueInputOption='USER_ENTERED', body=body).execute()

def update_all_spreadsheet(s3_client, sheet_client):
    all_buckets = _get_all_buckets(s3_client)
    _clear_spreadsheet(sheet_client, S3_ALL_SHEET)
    all_buckets = sorted(all_buckets, key=itemgetter(1))
    _fill_spreadsheet(sheet_client, S3_ALL_SHEET, all_buckets)

def _sync_tags(bucket_name, is_saved_now):
    """ Updates tags on buckets that are
        specifically marked "Saved" in the
        spreadsheet. Removes tags otherwise. 
    """
    tags, s3_tagging = _get_tags(bucket_name)
    _is_already_saved = _is_saved(tags)
    s3_tagging = boto3.resource('s3')
    if (_is_already_saved and is_saved_now) or (not _is_already_saved and not is_saved_now):
        print("Bucket '%s' doesn't need a tag change..."%bucket_name)
        return
    elif _is_already_saved and not is_saved_now:
        print("Removing saved tag from bucket '%s'..."%bucket_name)
        tags_to_add = [idx for idx, _dict in enumerate(tags) if 'Save' not in _dict]
        s3_tagging.delete()
        s3_tagging.put({ 'TagSet': tags_to_add })
    elif not _is_already_saved and is_saved_now:
        print("Adding save tag to bucket '%s'..."%bucket_name)
        s3_tagging.put({ 'TagSet': tags.append({'Save': 'true'}) })        

def update_old_spreadsheet(s3_client, sheet_client):
    all_buckets = _read_spreadsheet(sheet_client, S3_ALL_SHEET)
    existing_old_buckets = _read_spreadsheet(sheet_client, S3_OLD_SHEET)
    #for bucket in existing_old_buckets:
    #    _sync_tags(bucket[0], bucket[2])
    old_buckets = _get_old_buckets(all_buckets)
    to_write = []
    for old_bucket in old_buckets:
        for bucket in existing_old_buckets:
            if bucket[0] == old_bucket[0]:
                old_bucket[2] = bucket[2]
    _clear_spreadsheet(sheet_client, S3_OLD_SHEET)
    _fill_spreadsheet(sheet_client, S3_OLD_SHEET, old_buckets) 
    pass

def _get_tags(bucket_name):
    tags = []
    try:
        s3_tagging = boto3.resource('s3').BucketTagging(bucket_name)
        tags = s3_tagging.tag_set
    except Exception:
        pass
    return tags, s3_tagging

def _is_saved(tags):
    return True if 'Save' in str(tags) else False

def _get_all_buckets(s3_client):
    """ gets all s3 buckets for a given account as a list """
    all_buckets = []
    print("Collecting latest bucket information...")
    response = s3_client.list_buckets()
    print("Found %s buckets..."%str(len(response['Buckets'])))
    for bucket in response['Buckets']:
        # tag = _is_saved(_get_tags(bucket['Name']))
        all_buckets.append(
            [bucket['Name'],bucket['CreationDate'], 
            False]
        )
    print("Finished collecting bucket information...")
    return all_buckets

def apply_labels(s3_client):
    """ apply tags to the buckets that are marked as 'Saved' """
    pass

def _get_old_buckets(buckets):
    """ filters bucket list based on creation timestamp """
    old_buckets = []
    for bucket in buckets:
        if bucket[1] < (datetime.now() - timedelta(days=FILTER_BUCKET_DAYS)):
            old_buckets.append(bucket)
    return old_buckets

def main():
    s3_client = boto3.client('s3')
    sheet_client = common.init_spreadsheet_service()
    update_all_spreadsheet(s3_client, sheet_client) 
    update_old_spreadsheet(s3_client, sheet_client)

if __name__ == "__main__":
    main()
