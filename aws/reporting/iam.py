import datetime
import re

import boto3
import logging

logger = logging.getLogger(__name__)

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
        logger.info("{} Analyzing user {}".format(i, user['UserName']))
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
            logger.info("User {} is old".format(user["UserName"]))
        i += 1 
    return old_users

def get_users_for_a_cluster(users):
    filtered_users = []
    for user in users:
        print(user)
        logger.info("Analyzing user {}".format(user['UserName']))
        if user.get("UserName", "").startswith("cluster-"):
            filtered_users.append(user)
    return filtered_users

def delete_user(user):
    logger.info("Attempting to delete user {}".format(user['UserName']))
    iamRes = boto3.resource('iam')
    userRes = iamRes.User(user['UserName'])
    try:
        login_profile = userRes.LoginProfile()
        login_profile.delete()
    except Exception as e:
        logger.info("Failed deleting login profile {}".format(str(e)))
    for key in userRes.access_keys.all():
        try:
            key.delete()
        except:
            logger.info("Failed deleting key")
    for policy in userRes.policies.all():
        try:
            policy.delete()
        except:
            logger.info("Failed deleting policy")
    for policy in userRes.attached_policies.all():
        try:
            policy.delete()
        except:
            logger.info("Failed deleting policy")
    try:
        userRes.delete()
        logger.info("Deleted user")
    except:
        logger.info("Failed deleting user")

if __name__ == "__main__":
    import sys
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    users = get_all_users()
    users_to_delete = get_users_for_a_cluster(users)
    for user in users_to_delete:
        try:
            delete_user(user)
        except:
            logger.info("Failed deleting user {}".format(user['UserName']))