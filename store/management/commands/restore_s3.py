import os
import tempfile
from pathlib import Path

import boto3
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Restore DB backup from S3 (loaddata)."

    def add_arguments(self, parser):
        parser.add_argument("--bucket", default=os.getenv("S3_BACKUP_BUCKET", ""))
        parser.add_argument("--key", required=True)

    def handle(self, *args, **options):
        bucket = options["bucket"]
        key = options["key"]
        if not bucket:
            self.stderr.write(self.style.ERROR("S3 bucket not set. Use --bucket or S3_BACKUP_BUCKET."))
            return

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "restore.json"
            s3 = boto3.client("s3")
            s3.download_file(bucket, key, str(out_path))
            call_command("loaddata", str(out_path))
            self.stdout.write(self.style.SUCCESS(f"Restored backup from s3://{bucket}/{key}"))
