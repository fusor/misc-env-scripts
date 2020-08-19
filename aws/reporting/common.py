import boto3
import pickle
import datetime

def get_all_regions():
    regions = []
    ec2client = boto3.client('ec2')
    response = ec2client.describe_regions()
    for r in response['Regions']:
        regions.append(r['RegionName'])
    return regions

def reformat_data(data_items, keys):
    """ reformats data to compatible format for Google Sheets

        data_items (list): list of dicts, each item corresponds to an AWS resource
        keys (list): list of strings, keys in the original data to preserve,
                        all other keys in the original data will be removed
    """
    data = []
    for data_item in data_items:
        current_data_item = {}
        for key in keys:
            split_keys = key.split('.')
            data_entry = ''
            if split_keys[0] == 'Tags':
                for entry in data_item.get('Tags', []):
                    if split_keys[-1] in entry['Key']:
                        data_entry = entry['Value']
            else:
                data_entry = data_item
                for split_key in split_keys:
                    data_entry = data_entry.get(split_key, {})
            if data_entry == {}:
                data_entry = ''
            current_data_item[split_keys[-1]] = data_entry
        data.append(current_data_item)
    return data

def save_to_file(data, filename):
    with open('./{}'.format(filename), 'wb') as fp:
        pickle.dump(data, fp, protocol=pickle.HIGHEST_PROTOCOL)

def load_from_file(filename):
    data = None
    with open(filename, 'rb') as fp:
        data = pickle.load(fp)
    return data