from django.core.management.base import BaseCommand, CommandError
from apr.models import RegistryEntry


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        python manage.py generate_report 2015 1 optional_filename.txt
        """
        year = args[0]
        month = args[1]
        if len(args) > 2:
            filename = args[2]
        else:
            filename = "ampath-export-%s-%s.txt" % (year, month)

        from ampath import livebirths
        livebirths.serialize_entries(year, month, filename)