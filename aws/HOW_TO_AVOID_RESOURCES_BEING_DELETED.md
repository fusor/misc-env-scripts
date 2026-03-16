# How to Avoid Your AWS Resources Being Deleted

This document explains how the automated AWS cleanup process works and what you need to do to protect your resources from deletion.

## How the Cleanup Process Works

Our department runs automated scripts that identify and delete old or unused AWS resources. The system scans all AWS regions and tracks resources in a shared Google Spreadsheet. Resources that exceed certain age thresholds are scheduled for deletion unless you explicitly mark them as saved.

### What Gets Deleted and When

| Resource Type | Criteria for Deletion |
|---|---|
| **EC2 Instances** | Running for more than **30 days** and not marked as saved |
| **S3 Buckets** | Created more than **60 days** ago and not marked as saved |
| **EBS Volumes** | Status is `available` or `error` (not attached to any instance) -- deleted automatically during reports |
| **Classic ELBs** | Not assigned to any instances -- deleted automatically during reports |
| **VPCs** | No running EC2 instances (orphan) and not the default VPC |
| **IAM Users** | Username starts with `cluster-` |
| **Route53 Zones** | 4+ domain segments and fails connectivity test on port 22 |
| **CloudFormation Stacks** | Status is `CREATE_FAILED` / `DELETE_FAILED`, or contains no EC2 instances (unless EKS-managed) |

### Typical Schedule

- **Daily**: A report runs that refreshes the spreadsheet with current AWS resource data. Unused volumes and unassigned classic ELBs are deleted during this step.
- **Monday**: A deletion summary email is sent listing instances scheduled for termination. VPC cleanup runs.
- **Friday**: EC2 instances and VPCs are purged.
- **Annually**: A full-account purge targets all instances regardless of age. All previous "Save" markings are cleared, and you must re-mark anything you want to keep.

## How to Save Your EC2 Instances

1. **Open the shared Google Spreadsheet.** You should have received the link in a cleanup notification email. If not, ask your team lead for the spreadsheet URL.

2. **Go to the "EC2-Old-Instances" sheet tab.**

3. **Find your instance.** Look for your instance by checking the `Name`, `InstanceId`, or `owner` columns. You can use your browser's search (Ctrl+F / Cmd+F) to search by instance ID or your username.
  *. If your instance is less than the threshold (30 days old), you want to ensure it is not deleted, you will need to copy the entry from the "EC2-All-Instances" sheet to the "EC2-Old-Instances" sheet.  The important fields are `InstanceId`, and `Saved`.
  *. Note that the data under "EC2-Old-Instances" is recreated each week, the only entries which are persisted are the 'Saved' and 'Notes' values per 'InstanceId', everything else is overwritten.

4. **Type "Save" in the "Saved" column** for each instance you want to keep. The system checks for the word "save" anywhere in this field (case-insensitive), so any of the following will work:
   - `Save`
   - `Saved`
   - `save`
   - `Save - needed for testing`

5. **(Optional) Add a note in the "Notes" column.** Explain why the instance needs to stay running. This helps the team understand resource usage and is useful during annual reviews.

6. **Do this before the next scheduled purge.** After Monday's notification email, you have until Friday to mark your instances. Any instance without "save" in the Saved column will be terminated.

## How to Save Your S3 Buckets

1. **Go to the "S3-Old-Buckets" sheet tab** in the same spreadsheet.

2. **Find your bucket** by name in the `Name` column.

3. **Type exactly `Save`, `Saved`, or `save` in the "Saved" column.** Unlike EC2 instances, the S3 check requires an exact match -- partial matches or phrases like "Save this" will **not** protect your bucket.

## Important Things to Know

- **The spreadsheet is rebuilt on every report run.** When the daily report runs, the old-instances sheet is regenerated from scratch. Your `Saved` and `Notes` values are carried forward automatically as long as the instance still exists. You do not need to re-enter them every day.

- **During the annual purge, all "Save" markings are cleared.** You will be notified before this happens. You must go back into the spreadsheet and re-mark any resources you still need.

- **Volumes and classic ELBs have no "Save" mechanism.** Unattached EBS volumes and unassigned classic ELBs are deleted automatically during the report step. If you need a volume, make sure it is attached to a running instance. If you need a classic ELB, make sure it has instances assigned.

- **VPCs, IAM users, Route53 zones, and CloudFormation stacks have no "Save" mechanism.** These are deleted based on their structural state (orphaned, failed, unreachable), not age. To protect a VPC, ensure it has at least one running EC2 instance.

- **The notification email lists what will be deleted.** Review it carefully. It groups instances by owner and GUID, and lists any orphan instances that could not be associated with an owner.

## Quick Reference

| I want to save... | Where to go | What to type in "Saved" column |
|---|---|---|
| An EC2 instance | "EC2-Old-Instances" sheet | Anything containing "save" (case-insensitive) |
| An S3 bucket | "S3-Old-Buckets" sheet | Exactly `Save`, `Saved`, or `save` |
| An EBS volume | N/A | Attach it to a running instance |
| A VPC | N/A | Ensure it has at least one running instance |

## Questions?

If you cannot find the spreadsheet, did not receive a notification email, or have questions about the cleanup process, contact your team lead or the infrastructure team.
