import boto3
import logging
from socket import socket
from socket import AF_INET, SOCK_STREAM
from socket import gaierror, herror, timeout


logger = logging.getLogger(__name__)

def connection_test(base_url: str):
    responses = []
    limit = 6
    clientvm_ping_path = "clientvm.{}".format(base_url)
    logger.info("Running test on '{}'".format(clientvm_ping_path))
    for i in range(limit):
        s = socket(AF_INET, SOCK_STREAM)
        try:
            s.settimeout(2)
            s.connect((clientvm_ping_path, 22))
            s.shutdown(2)
            return True
        except (gaierror, herror, timeout):
            responses.append(1)
        except:
            responses.append(0)
    return True if responses.\
        count(0) > (limit/2) else False

def delete_hosted_zones(dry_run = False):
    client = boto3.client('route53')
    deleteable_zones = []
    try:
        zones = client.list_hosted_zones(MaxItems="500")
        zoneResources = zones.get('HostedZones', [])
        logger.info("Found {} zones".format(len(zoneResources)))
        for zone in zoneResources:
            zoneName = zone.get("Name", "")[:-1]
            if len(zoneName.split(".")) < 4:
                logger.info("Skipping zone {}".format(zoneName))
                continue
            elif zoneName != "" and connection_test(zoneName):
                logger.info(">>> Test successful zone {}".format(zoneName))
                continue
            else:
                logger.info("Test unsuccessful zone {}".format(zoneName))
                deleteable_zones.append({
                    "ZoneName": zoneName,
                    "ZoneId": zone.get("Id"),
                })
                record_sets = client.list_resource_record_sets(HostedZoneId=zone.get("Id", ""))
                changes = []
                for record_set in record_sets.get("ResourceRecordSets", []):
                    typ = record_set.get("Type", "")
                    if typ != "NS" and typ != "SOA":
                        change = {
                            "Action": "DELETE",
                            "ResourceRecordSet": record_set,
                        }
                        changes.append(change)
                if len(changes) > 0:
                    try:
                        client.change_resource_record_sets(
                            HostedZoneId=zone.get("Id", ""),
                            ChangeBatch={
                                'Changes': changes,
                            }
                        )
                        logger.info("Changed record sets in zone {}".format(zoneName))
                    except Exception as e:
                        logger.info("Failed changing record sets in zone {} {}".format(zoneName, str(e)))
                try:
                    client.delete_hosted_zone(Id=zone.get("Id"))
                    logger.info("Deleted zone {}".format(zoneName))
                except Exception as e:
                    logger.info("Failed deleting zone {}".format(zoneName))
    except Exception as e:
        logger.error("Error getting hosted zones {}".format(str(e)))

if __name__ == "__main__":
    import sys
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    delete_hosted_zones()