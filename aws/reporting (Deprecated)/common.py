from __future__ import print_function
import boto3    
import datetime
import os.path
import pickle
import pprint
import pytz 
import sys

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SPREADSHEET_ID = '1XOMu12uPJgtX_gN3mUTQu89kArzBft4edhbkXqlae5M'

#For spreadsheet of older instances
OLDER_LABELS = [
    "Saved",
    "Cost to date",
    "Hourly Cost",
    "Region",
 #   "AvailabilityZone",
    "InstanceId",
    "InstanceType",
    "LaunchTime",
    "owner",
    "Name",
    "guid",
    "Notes"
]

#For spreadsheet of all instances
ALL_LABELS = [
    "Daily Cost",
    "Hourly Cost",
    "Region",
    "InstanceId",
    "InstanceType",
    "LaunchTime",
    "owner",
    "Name",
    "guid",
]

# https://aws.amazon.com/ec2/pricing/on-demand/
# Updated 1/25/2020
HOUR_COSTS = {
    "t2.micro" : "0.0116",
    "t2.small" : "0.023",
    "t2.medium": "0.046",
    "t2.large" : "0.0928",
    "m4.large" : "0.10",
    "m4.xlarge": "0.20",
    "m4.2xlarge": "0.40",
    "m4.4xlarge": "0.80",
    "m5.large": "0.096", 
    "m5.xlarge": "0.192",
    "m5.2xlarge": "0.384",
    "m5.4xlarge": "0.768"
}


def init_spreadsheet_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    return sheet 

def get_range_instances_start():
    range_name = 'Older Instances!B1:Z'
    return range_name 

def estimate_cost(instance):
    instance_type = instance['InstanceType']
    
    then = instance['LaunchTime']
    now = datetime.datetime.now(then.tzinfo)    
    duration = now - then                        
    duration_in_s = duration.total_seconds()  
    hours = divmod(duration_in_s, 3600)[0] 

    # We want to warn if we can't find the cost of a certain instance but we want to continue
    # with processing the report for rest of instances.
    if instance_type not in HOUR_COSTS:
        print("\n **** \n\n\n *** *** Can't find cost for '%s' *** *** \n\n\n **** \n" % (instance_type))

    hour_cost = HOUR_COSTS[instance_type]
    cost_to_date = int(hours) * float(HOUR_COSTS[instance_type])
    return (hour_cost, cost_to_date)


def get_existing_data_from_spreadsheet(sheet_service):
    """
    Returns a dictionary:
     {
         'InstanceId': {
            'Notes': "",
            'Saved': "",
            'Region': "",
        }
     }
    """
    range_name = get_range_instances_start()
    result = sheet_service.values().get(
        spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    rows = result.get('values', [])
    
    existing_data_from_spreadsheet = {}
    
    if len(rows) < 2:
        return existing_data_from_spreadsheet
    
    label_row = rows[1]
    if 'InstanceId' not in label_row or 'Saved' not in label_row or 'Notes' not in label_row:
        return existing_data_from_spreadsheet
        
    instance_id_column = label_row.index('InstanceId')
    saved_column_index = label_row.index('Saved')
    notes_column_index = label_row.index('Notes')
    region_column_index = label_row.index('Region')

    for r in rows[2:]:
        existing_data_from_spreadsheet[r[instance_id_column]] = {}
        existing_data_from_spreadsheet[r[instance_id_column]]['InstanceId'] = r[instance_id_column]

        if len(r) > saved_column_index:
            existing_saved = r[saved_column_index]
        else: 
            existing_saved = ""
        existing_data_from_spreadsheet[r[instance_id_column]]['Saved'] = existing_saved

        if len(r) > notes_column_index: 
            existing_notes = r[notes_column_index]
        else:
            existing_notes = ""
        existing_data_from_spreadsheet[r[instance_id_column]]['Notes'] = existing_notes
        
        if len(r) > region_column_index: 
            existing_region = r[region_column_index]
        else:
            existing_region = ""
        existing_data_from_spreadsheet[r[instance_id_column]]['Region'] = existing_region

    return existing_data_from_spreadsheet


def get_existing_data(data, inst_id, key):
    # We want to return the field of a given key from data in the spreadsheet matching a specific instance id
    if data.has_key(inst_id):
        if data[inst_id].has_key(key):
            return data[inst_id][key]
    return ""

def get_message():
    eastern_tz = pytz.timezone('US/Eastern')
    return ["", "Last Run", datetime.datetime.now(eastern_tz).strftime("%H:%M:%s %B %d, %Y")]

def get_all_message():
    eastern_tz = pytz.timezone('US/Eastern')
    return ["", "Last Run", datetime.datetime.now(eastern_tz).strftime("%H:%M:%s %B %d, %Y"), "", "", "Total Daily Cost Estimate", "=sum(b3:b9999)"]

def read_spreadsheet(sheet_service):
    return get_existing_data_from_spreadsheet(sheet_service)    

def delete_prior_entries_from_spreadsheet(sheet_service, sheet_range):

    batch_clear_values_request_body = {
       'ranges': [sheet_range],
    }

    request = sheet_service.values().batchClear(spreadsheetId=SPREADSHEET_ID, body=batch_clear_values_request_body)
    response = request.execute()
    print("Result from clearing prior entries:  %s" % (response))


def update_summary_spreadsheet(sheet_service, instances):
    
    # Ensure header is written, will overwrite with time/date stamp on each run
    eastern_tz = pytz.timezone('US/Eastern')
    values = [
        ["", "Last Run", datetime.datetime.now(eastern_tz).strftime("%H:%M:%S %B %d, %Y")],
        ["", "Date", "Estimated Daily Cost"]
    ]
    body = {
        'values': values
    }
    print("Summary Header:  Attempting to write <%s>" % (body))
    result = sheet_service.values().update(
        spreadsheetId=SPREADSHEET_ID, range='Summary!A1:Z',
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} rows and {1} cells updated.'.format(result.get('updatedRows'), result.get('updatedCells')))
     
    # Compute the estimated daily cost and insert it as a new row
    estimated_daily_cost = 0.0
    for inst in instances:
        cost = estimate_cost(inst)
        daily_cost = 24.0 * float(cost[0])
        print("Adding %s to daily cost of %s" % (daily_cost, estimated_daily_cost))
        estimated_daily_cost += daily_cost
    
    now = datetime.datetime.now(eastern_tz).strftime("%Y %B %d %H:%M:%S")
    values = [
        ["", now, estimated_daily_cost]
    ]
    body = {
        'values': values
    }

    print("Summary Row:  Attempting to write <%s>" % (body))
    result = sheet_service.values().append(
       spreadsheetId=SPREADSHEET_ID, range='Summary!A3',
       valueInputOption='USER_ENTERED', 
       insertDataOption='INSERT_ROWS',
       body=body).execute()
    print('{0} rows and {1} cells updated.'.format(result.get('updatedRows'), result.get('updatedCells')))

def update_all_running_spreadsheet(sheet_service, instances):
    labels = ALL_LABELS
    values = []
    values.append(get_all_message())
    values.append(labels)

    for inst in instances:
        entry = []
        cost = estimate_cost(inst)
        for key in labels:
            value = ""
            if key == 'Daily Cost':
                value = 24.0 * float(cost[0])
            elif key == 'Hourly Cost':
                value = cost[0]
            else:
                if inst.has_key(key):
                    value = inst[key]
                else:
                    value = ""
                
            if isinstance(value, datetime.datetime):
                entry.append(value.strftime("%B %d, %Y"))
            else:
                entry.append(value)
    
        values.append(entry)

    body = {
        'values': values
    }

    delete_prior_entries_from_spreadsheet(sheet_service, 'All Instances!B3:Z')
    result = sheet_service.values().update(
        spreadsheetId=SPREADSHEET_ID, range='All Instances!B1:Z',
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} rows and {1} cells updated.'.format(result.get('updatedRows'), result.get('updatedCells')))


def update_spreadsheet(sheet_service, instances):
    # Read spreadsheet for existing entries of Saved and Notes
    # Update existing instances for Saved and Notes
    # Overwrite all instance data in spreadsheet
    
    if len(instances) < 1:
        print("Unable to process zero length instances")
        sys.exit()

    
    labels = OLDER_LABELS
    values = []
    values.append(get_message())
    values.append(labels)
    existing_data = get_existing_data_from_spreadsheet(sheet_service)    

    for inst in instances:
        entry = []
        cost = estimate_cost(inst)
        for key in labels:
            value = ""
            if key == 'Cost to date':
                value = cost[1]
            elif key == 'Hourly Cost':
                value = cost[0]
            elif key == 'Saved':
                value = get_existing_data(existing_data, inst['InstanceId'], 'Saved')
            elif key == 'Notes':
                value = get_existing_data(existing_data, inst['InstanceId'], 'Notes')
            else:
                if inst.has_key(key):
                    value = inst[key]
                else:
                    value = ""
                
            if isinstance(value, datetime.datetime):
                entry.append(value.strftime("%B %d, %Y"))
            else:
                entry.append(value)
    
        values.append(entry)

    body = {
        'values': values
    }
    print(body)
    print (labels)

    delete_prior_entries_from_spreadsheet(sheet_service, 'Older Instances!B3:Z')
    range_name = get_range_instances_start()    
    result = sheet_service.values().update(
        spreadsheetId=SPREADSHEET_ID, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} rows and {1} cells updated.'.format(result.get('updatedRows'), result.get('updatedCells')))


def get_all_region_names():
    regions = []
    client = boto3.client('ec2')
    response = client.describe_regions()
    for r in response['Regions']:
        regions.append(r['RegionName'])
    return regions

def get_all_instances_in_regions(regions):
    all_instances = {}
    for r in regions:
        all_instances[r] = get_all_instances_per_region(r)
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
    instances.sort(cmp_LaunchTime)
    return instances

def reformat_instance_data(raw_instances):
    instances = []
    for region in raw_instances:
        for r in raw_instances[region]:
            inst = {}
            inst['InstanceId'] = r['InstanceId']
            inst['InstanceType'] = r['InstanceType']
            inst['LaunchTime'] = r['LaunchTime']
            inst['Region'] = region
            #inst['AvailabilityZone'] = r['Placement']['AvailabilityZone']
            #inst['Arn'] = ""
            #if r.has_key("IamInstanceProfile"):
            #    if r["IamInstanceProfile"].has_key("Arn"):
            #        inst['Arn'] = r['IamInstanceProfile']['Arn']
            for entry in r["Tags"]:
                for k in ["owner", "Name", "guid"]:
                    if k in entry["Key"]:
                        inst[k] = entry["Value"]
            instances.append(inst)
    return instances

def cmp_LaunchTime(a, b):
    if a["LaunchTime"] > b["LaunchTime"]:
        return 1
    elif a["LaunchTime"] == b["LaunchTime"]:
        return 0
    else:
        return -1


def get_older_than_by_days(instances, cutOffInDays):
    filteredInstances = {}
    for region in instances:
        filteredInstances[region] = []
        for inst in instances[region]:
            tzinfo = inst["LaunchTime"].tzinfo
            if inst["LaunchTime"] < datetime.datetime.now(tzinfo)-datetime.timedelta(days=cutOffInDays):
                filteredInstances[region].append(inst)
            else:
                pass
    return filteredInstances
