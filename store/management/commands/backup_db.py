from datetime import datetime
from pathlib import Path

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Create a JSON backup using dumpdata."

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", default="backups", help="Directory to write backups.")

    def handle(self, *args, **options):
        out_dir = Path(options["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = out_dir / f"backup_{timestamp}.json"
        call_command("dumpdata", "--natural-foreign", "--natural-primary", "--indent", "2", output=str(out_file))
        self.stdout.write(self.style.SUCCESS(f"Backup written to {out_file}"))
