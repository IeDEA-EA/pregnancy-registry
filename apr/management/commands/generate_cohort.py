from django.core.management.base import BaseCommand, CommandError
from apr.models import RegistryEntry


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        python manage.py generate_cohort 2015 1,2,3 100588
        """
        year = args[0]
        months = args[1].split(',')
        if len(args) > 2:
            apr_id_start = args[2]
        else:
            apr_id_start = RegistryEntry.get_max_apr_id()

        from ampath import livebirths
        for month in months:
            livebirths.full_monthly_cohort_generation(year=int(year), 
                month=int(month), apr_starting_id=int(apr_id_start))
            apr_id_start = RegistryEntry.get_max_apr_id()+1
        