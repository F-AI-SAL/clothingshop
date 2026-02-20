import os
import tempfile
from pathlib import Path

import boto3
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a DB backup (dumpdata) and upload to S3."

    def add_arguments(self, parser):
        parser.add_argument("--bucket", default=os.getenv("S3_BACKUP_BUCKET", ""))
        parser.add_argument("--prefix", default=os.getenv("S3_BACKUP_PREFIX", "backups"))
        parser.add_argument("--retention-days", type=int, default=int(os.getenv("S3_BACKUP_RETENTION_DAYS", "30")))

    def handle(self, *args, **options):
        bucket = options["bucket"]
        prefix = options["prefix"].strip("/")
        retention_days = options["retention_days"]
        if not bucket:
            self.stderr.write(self.style.ERROR("S3 bucket not set. Use --bucket or S3_BACKUP_BUCKET."))
            return

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "backup.json"
            call_command("dumpdata", "--natural-foreign", "--natural-primary", "--indent", "2", output=str(out_path))

            s3 = boto3.client("s3")
            key = f"{prefix}/backup_{out_path.stat().st_mtime_ns}.json"
            s3.upload_file(str(out_path), bucket, key)
            self.stdout.write(self.style.SUCCESS(f"Uploaded backup to s3://{bucket}/{key}"))

            # retention cleanup
            if retention_days > 0:
                cutoff = out_path.stat().st_mtime - (retention_days * 86400)
                paginator = s3.get_paginator("list_objects_v2")
                to_delete = []
                for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/"):
                    for obj in page.get("Contents", []):
                        if obj["LastModified"].timestamp() < cutoff:
                            to_delete.append({"Key": obj["Key"]})
                    if len(to_delete) >= 1000:
                        s3.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})
                        to_delete = []
                if to_delete:
                    s3.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})
