import re
import sys
import boto3
import datetime
from common import save_to_file, load_from_file

def get_all_users():
    users = []
    isTruncated = True
    marker = ''
    while isTruncated:
        if marker:
            response = boto3.client('iam').list_users(Marker=marker)
        else:
            response = boto3.client('iam').list_users()
        paginatedUsers = response['Users']
        users.extend(paginatedUsers)
        isTruncated = response.get('IsTruncated', False)
        marker = response.get('Marker', '')
    return users

# returns old users based on threshold values
# users             : all users
# createdThreshold  : user creation date threshold
# lastUsedThreshold : user last active threshold
def get_old_users(users, createdThreshold=60, lastUsedThreshold=120):
    old_users = []
    i = 1
    for user in users:
        print("{} Analyzing user {}".format(i, user['UserName']))
        userResource = boto3.resource('iam').User(user['UserName'])
        allUsageDates = []
        if isinstance(userResource.password_last_used, datetime.date):
            allUsageDates.append(userResource.password_last_used)
        for key in userResource.access_keys.all():
            res = boto3.client('iam').get_access_key_last_used(AccessKeyId=key.id)
            d = res.get('AccessKeyLastUsed', {}).get('LastUsedDate')
            if isinstance(d, datetime.date):
                allUsageDates.append(d)
        createdThresholdAgo = (datetime.datetime.now() - userResource.create_date.replace(tzinfo=None)).days > createdThreshold
        if allUsageDates:
            usedThresholdAgo = (datetime.datetime.now() - max(allUsageDates).replace(tzinfo=None)).days > lastUsedThreshold
        else:
            usedThresholdAgo = False
        if createdThresholdAgo and usedThresholdAgo and not re.match(r'[^@]+@[^@]+\.[^@]+', user['UserName']):
            old_users.append(user)
            print("User {} is old".format(user["UserName"]))
        i += 1 
    return old_users

def delete_user(user):
    print("Attempting to delete user {}".format(user['UserName']))
    iamRes = boto3.resource('iam')
    userRes = iamRes.User(user['UserName'])
    try:
        login_profile = userRes.LoginProfile()
        login_profile.delete()
    except Exception as e:
        print("Failed deleting login profile {}".format(str(e)))
    for key in userRes.access_keys.all():
        try:
            key.delete()
        except:
            print("Failed deleting key")
    for policy in userRes.policies.all():
        try:
            policy.delete()
        except:
            print("Failed deleting policy")
    for policy in userRes.attached_policies.all():
        try:
            policy.delete()
        except:
            print("Failed deleting policy")
    try:
        userRes.delete()
        print("Deleted user")
    except:
        print("Failed deleting user")

users = get_all_users()
old_users = get_old_users(users)
for user in old_users:
    try:
        delete_user(user)
    except:
        print("Failed deleting user {}".format(user['UserName']))