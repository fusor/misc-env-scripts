#! /usr/bin/env python

import common

def main():
    cutOff = 30
    
    sheet_service = common.init_spreadsheet_service()
    
    regions = common.get_all_region_names()
    #regions = ["us-east-1"]
    
    instances = common.get_all_instances_in_regions(regions)
    all_data = common.reformat_instance_data(instances)
    print("%s instances found running" % ((len(all_data))))
    common.update_all_running_spreadsheet(sheet_service, all_data)
    
    common.update_summary_spreadsheet(sheet_service, all_data)


    filtered_instances = common.get_older_than_by_days(instances, cutOff)
    data = common.reformat_instance_data(filtered_instances)
    print("%s instances older than %s days" % ((len(data)), cutOff))
    common.update_spreadsheet(sheet_service, data)




if __name__ == '__main__':
    main()
