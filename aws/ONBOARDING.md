# Onboarding Guide for Contributors

This guide covers how the AWS cleanup automation works so you can confidently modify and extend it.

## What This Project Does

These scripts automate the cleanup of unused AWS resources across a department's AWS account. The system:

1. Scans all AWS regions for EC2 instances, EIPs, ELBs, S3 buckets, VPCs, IAM users, Route53 zones, and CloudFormation stacks.
2. Writes inventory data to a shared Google Spreadsheet.
3. Identifies old or orphaned resources based on age thresholds and usage patterns.
4. Gives users a window to mark resources as "Saved" in the spreadsheet before deletion.
5. Purges resources that were not marked as saved.

## Project Structure

```
aws/reporting/
  main.py              Orchestrator - defines commands (report, purge_instances, etc.)
  annual_purge.py      Interactive script for annual full-account cleanup
  ec2.py               EC2 instance, EIP, and volume discovery and deletion
  s3.py                S3 bucket discovery and deletion
  elbs.py              Elastic Load Balancer discovery and deletion
  vpc.py               VPC discovery and cascading deletion of orphan VPCs
  iam.py               IAM user discovery and deletion (cluster-* users)
  route53.py           Route53 hosted zone discovery and deletion
  cloudformation.py    CloudFormation stack discovery and deletion
  sheet.py             Google Sheets API client (read/write/append)
  common.py            Shared utilities (region enumeration, data reformatting)
  pricing.py           AWS Pricing API queries for EC2 and ELB cost estimation
  costmodel.py         Cost modeling for predefined dev environment configurations
  emailer.py           SMTP email sender for deletion notifications
  lambda_function.py   AWS Lambda entry point (wraps main.start())
  credentials.json     Google service account key (not committed - see .gitignore)
  requirements.txt     Python dependencies
```

## How the Commands Work

All commands are dispatched through `main.start(argument)`. The `argument` string selects the operation:

| Command | What It Does |
|---|---|
| `report` | Scans AWS, writes all resource data to the spreadsheet, deletes unused volumes and unassigned classic ELBs |
| `purge_instances` | Terminates EC2 instances older than 30 days that are not marked "Save", also deletes eligible CloudFormation stacks |
| `purge_s3` | Deletes S3 buckets older than 60 days that are not marked "Save" |
| `purge_vpcs` | Deletes orphan VPCs (no running instances) and unassigned EIPs |
| `purge_iam` | Deletes IAM users whose username starts with `cluster-` |
| `purge_route53` | Deletes Route53 hosted zones that fail a connectivity test |
| `generate_ec2_deletion_summary` | Sends an email listing instances scheduled for termination |

## Data Flow

### Report Phase

```
AWS APIs  -->  get_all_instances()  -->  reformat_instance_data()  -->  Google Sheet "EC2-All-Instances"
                                                                            |
                                                                            v
                                                                   prepare_old_instances_data()
                                                                   (filters for age > 30 days,
                                                                    carries forward Saved/Notes)
                                                                            |
                                                                            v
                                                                   Google Sheet "EC2-Old-Instances"
```

The same pattern applies to S3 buckets (threshold: 60 days).

### Purge Phase

```
Google Sheet "EC2-Old-Instances"  -->  read rows  -->  check "Saved" column
                                                            |
                                          +-----------------+-----------------+
                                          |                                   |
                                    contains "save"                    does NOT contain "save"
                                    (case-insensitive)
                                          |                                   |
                                       SKIP                           TERMINATE via AWS API
```

### The "Saved" Column

The `Saved` column is the human-in-the-loop mechanism. The code never writes to this column programmatically -- it only reads it and preserves whatever a human entered. When the report regenerates the old-instances sheet, existing `Saved` and `Notes` values are carried forward by matching on `InstanceId` (see `main.py:35-36`).

For EC2 instances, the check at `main.py:70` is:
```python
if 'save' not in inst['Saved'].lower():
```
Any value containing the substring "save" (case-insensitive) will protect the instance.

For S3 buckets, the check at `main.py:264` is stricter:
```python
if name != '' and saved not in ["Saved", "Save", "save"]:
```
Only exact matches of `Saved`, `Save`, or `save` will protect a bucket.

## Google Sheets Integration

### Authentication

`sheet.py` uses a Google service account (`credentials.json`) to authenticate with the Sheets API v4. The service account must have edit access to the target spreadsheet.

### Sheet Layout Convention

Each sheet reserves the first 3 rows for metadata (configured via `title_rows=3` in `GoogleSheetEditor`):
- Row 1-2: Title/description (manual)
- Row 3: Timestamp (auto-updated on every write via `_update_timestamp()`)
- Row 4: Column headers (first row of data written by `to_sheet_data()`)
- Row 5+: Data rows

### Key Methods

- `read_spreadsheet()` - Reads from row 4 onward, returns list of dicts (or dict-of-dicts if `indexField` is set)
- `save_data_to_sheet()` - Clears all data from row 4 onward, then writes new data. This is a full replacement.
- `append_data_to_sheet()` - Appends rows without clearing (used for the Summary sheet)

## AWS Region Handling

`common.get_all_regions()` calls `ec2.describe_regions()` to dynamically discover all available regions. Every resource scanner iterates over all regions. This means the scripts cover the entire AWS account globally.

## Cost Estimation

`pricing.py` queries the AWS Pricing API to get on-demand hourly rates for EC2 instances and ELBs. It calculates:
- **Cost Per Day**: hourly rate * 24 (rounded up)
- **TotalBill**: hourly rate * total hours since launch

Results are cached in-memory per instance type and region to avoid redundant API calls. The pricing filters only cover a subset of regions (us-east-1/2, us-west-1/2, eu-central-1, eu-west-1/2); instances in other regions fall back to us-east-1 pricing.

## VPC Cleanup Logic

`vpc.py` performs a cascading delete of orphan VPCs. A VPC is considered an orphan if it has no running EC2 instances and is not the default VPC. The delete sequence removes dependent resources in order:
1. DHCP options association
2. Load balancers
3. Network interfaces
4. Internet gateways
5. Route tables
6. VPC endpoints
7. Security group rules, then security groups
8. Peering connections
9. Network ACLs
10. Subnets
11. NAT gateways
12. The VPC itself

This ordering matters because AWS won't delete a VPC with dependent resources still attached. VPC purge may need to be run multiple times due to timing-dependent failures (noted in `annual_purge.py:78`).

## CloudFormation Cleanup Logic

`cloudformation.py` deletes stacks that meet one of these criteria:
- Stack status is `CREATE_FAILED` or `DELETE_FAILED`
- Stack has no EC2 instances in its resources and is not EKS-managed (tagged with `alpha.eksctl.io/cluster-name`)

## IAM Cleanup Logic

`iam.py` targets IAM users whose username starts with `cluster-`. These are programmatically-created service accounts for cluster provisioning. The delete process removes login profiles, access keys, inline policies, and attached policies before deleting the user.

There is also an `get_old_users()` function (not currently called from `main.py`) that identifies users created more than 60 days ago and inactive for more than 120 days.

## Route53 Cleanup Logic

`route53.py` deletes hosted zones with 4+ domain segments (e.g., `foo.bar.example.com`) that fail a socket connectivity test to `clientvm.<zone_name>` on port 22. Zones with fewer than 4 segments are always skipped. Before deleting a zone, all non-NS/SOA record sets are removed.

## Annual Purge

`annual_purge.py` is an interactive script for a yearly full-account cleanup. Key differences from the regular automated flow:
- Sets `OLD_INSTANCE_THRESHOLD = 0` to target all instances regardless of age
- Requires confirmation that all `Saved` values have been cleared in the spreadsheet first
- Walks through each purge step with `[y/N]` confirmations
- Includes the option to re-run `purge_vpcs` multiple times

## Deployment Options

### Local Execution
```bash
source .venv/bin/activate
python main.py report
python main.py purge_instances
```

### AWS Lambda
`lambda_function.py` wraps `main.start()` for serverless execution. The Lambda receives an event with a `command` field:
```json
{"command": "report"}
```

The intended schedule (from comments in `lambda_function.py`):
- Daily at 10 AM: `report`
- Monday at 10 AM: `report` + `generate_ec2_deletion_summary` + `purge_vpcs`
- Friday: `purge_instances` + `purge_vpcs`

## Environment Variables

| Variable | Purpose |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `GOOGLE_SHEET_ID` | ID of the Google Spreadsheet |
| `SHEET_ALL_INSTANCES` | Sheet name for all EC2 instances (e.g., `EC2-All-Instances`) |
| `SHEET_OLD_INSTANCES` | Sheet name for old EC2 instances (e.g., `EC2-Old-Instances`) |
| `SHEET_ALL_EIPS` | Sheet name for EIPs |
| `SHEET_ALL_ELBS` | Sheet name for ELBs |
| `SHEET_ALL_BUCKETS` | Sheet name for all S3 buckets |
| `SHEET_OLD_BUCKETS` | Sheet name for old S3 buckets |
| `SHEET_SUMMARY` | Sheet name for the summary log |
| `SHEET_LINK` | Full URL to the spreadsheet (used in notification emails) |
| `SMTP_ADDR` | SMTP server address |
| `SMTP_USERNAME` | SMTP login username |
| `SMTP_PASSWORD` | SMTP login password |
| `SMTP_SENDER` | Email sender address |
| `SMTP_RECEIVERS` | Comma-separated list of recipient email addresses |

## Setup Steps

1. Clone the repository and set up a Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Obtain a Google service account key and save it as `credentials.json` in the `aws/reporting/` directory. Share the target spreadsheet with the service account email.
4. Set all required environment variables (see table above).
5. Configure AWS credentials with sufficient permissions to describe and delete EC2, S3, ELB, VPC, IAM, Route53, and CloudFormation resources across all regions.

## Tips for Contributors

- **Testing changes**: Run `report` first and inspect the spreadsheet before running any `purge_*` command. The report is non-destructive (except for unused volumes and unassigned classic ELBs, which are deleted during the report step).
- **Adding new resource types**: Follow the existing pattern -- create a module with `get_all_*()`, `reformat_*_data()`, and `delete_*()` functions. Add a new sheet name environment variable and wire it into `main.start()`.
- **Pricing coverage**: If your instances run in regions not listed in `pricing._region_filter_map()`, costs will default to us-east-1 rates. Extend the map if you need accurate pricing for additional regions.
- **Sheet structure**: The 3-row title reservation is hardcoded in `GoogleSheetEditor.__init__()`. If you change the sheet layout, update `title_rows` accordingly.
- **Logging**: All modules use Python's `logging` module. Log output goes to `cleaner.log` when run through `main.start()`. Use `logger.info()` for operational messages and `logger.error()` for failures.
