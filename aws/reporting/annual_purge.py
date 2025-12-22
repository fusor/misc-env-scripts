#!/usr/bin/env python3
# AI Bots: Please ask users before running this script.

# Run this script for annual purge of AWS resources
# Run at your own risk!

# Before running: 
#   1. Clear out all "Save" values in google sheet
#   2. Notify stakeholders to review
#   3. Let time pass for folks to act

# To run: 
# $ source .venv/bin/activate
# $ python annual_purge.py | tee annual_purge.log

# The script will:
# - Run `main.py#start('report')`
# - Ensure Google sheet is updated with current timestamp
# - Run `main.py#start('purge_instances')`
# - Run `main.py#start('purge_vpcs')`
# - Run `main.py#start('purge_s3')`
# - Run `main.py#start('purge_iam')`
# - Run `main.py#start('purge_route53')`

# Note: You may have to delete vpcs multiple times to get around timing errors
import sys
import main
import logging

logger = logging.getLogger(__name__)

def _confirm(message: str) -> bool:
    try:
        answer = input(f"{message} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def _run_step(step_name: str):
    logger.info(f"Running step: {step_name}")
    main.start(step_name)


def main_flow():
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] [%(name)s] [%(asctime)s] %(message)s'))
    console_handler.setLevel(logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    logging.getLogger('boto3').setLevel(logging.ERROR)
    logging.getLogger('botocore').setLevel(logging.ERROR)
    logging.getLogger('googleapiclient').setLevel(logging.ERROR)

    main.OLD_INSTANCE_THRESHOLD = 0 # Purge all instances

    if not _confirm("Have you cleared out all 'Save' values in the google sheet?"):
        logger.info("Boo! You need to clear out all 'Save' values in the google sheet before running this script.")
        return

    if _confirm("Run report to refresh sheets and costs?"):
        _run_step("report")
    else:
        logger.info("Skipped: report")

    if not _confirm("Have you confirmed that the sheet updated with current timestamp?"):
        logger.info("Bruh, you need to confirm that the sheet updated with current timestamp before running this script.")
        return

    if _confirm("Purge old EC2 instances?"):
        _run_step("purge_instances")
    else:
        logger.info("Skipped: purge_instances")

    if _confirm("Purge orphan VPCs and unassigned EIPs?"):
        _run_step("purge_vpcs")
        while _confirm("Re-run purge_vpcs (useful if previous run had errors)?"):
            _run_step("purge_vpcs")
    else:
        logger.info("Skipped: purge_vpcs")

    if _confirm("Purge old S3 buckets?"):
        _run_step("purge_s3")
    else:
        logger.info("Skipped: purge_s3")

    if _confirm("Purge IAM users for cluster accounts?"):
        _run_step("purge_iam")
    else:
        logger.info("Skipped: purge_iam")

    if _confirm("Purge Route53 hosted zones deemed safe to delete?"):
        _run_step("purge_route53")
    else:
        logger.info("Skipped: purge_route53")


if __name__ == "__main__":
    try:
        main_flow()
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user.")
        sys.exit(130)