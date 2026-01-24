from celery import shared_task
from django.core.management import call_command


@shared_task
def run_backup(output_dir="backups"):
    call_command("backup_db", "--output-dir", output_dir)


@shared_task
def run_anonymize(days=365):
    call_command("anonymize_orders", "--days", str(days))
