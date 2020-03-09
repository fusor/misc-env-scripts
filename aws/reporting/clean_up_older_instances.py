#! /usr/bin/env python

import boto3
import pprint
import sys 

import common

def get_instances_to_delete():
    # Read from google spreadsheet
    #   We want to read the list of potential instances to delete from the spreadsheet
    #   Some of the instances need to be saved, so we need to determine
    #   - Which do we save (any instance with text in the Saved column means we want to save it)
    #   - Which can be deleted (any instance with no text in Saved)
    sheet_service = common.init_spreadsheet_service()
    entries = common.read_spreadsheet(sheet_service)
    to_delete = []
    for instanceId in entries:
        entry = entries[instanceId]
        if entry['Saved'] == "":
            to_delete.append(entry)
    return to_delete

def print_api_termination(entries):
    for entry in entries:
        instance_id = entry['InstanceId']
        region = entry['Region']
        ec2 = boto3.resource('ec2', region_name=region)
        termination = ec2.Instance(instance_id).describe_attribute(Attribute='disableApiTermination')
        print "%s disableApiTermination = %s" % (instance_id, termination)




def main():
    to_delete = get_instances_to_delete()
    print "Safe to delete: %s instances" % (len(to_delete))
    #pprint.pprint(to_delete)
    
    for entry in to_delete:
        if entry['Saved'] != "":
            print "Abort, something went wrong, found an instance that should be Saved:"
            pprint.pprint(entry)
            sys.exit(1)
        
        instance_id = entry['InstanceId']
        region = entry['Region']
        ec2 = boto3.resource('ec2', region_name=region)
        termination = ec2.Instance(instance_id).terminate()
        print "%s:  termination output:\n %s" % (instance_id, termination)


if __name__ == '__main__':
    main()
