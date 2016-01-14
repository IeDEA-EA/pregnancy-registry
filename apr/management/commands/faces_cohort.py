from django.core.management.base import BaseCommand, CommandError
from apr.models import RegistryEntry
from faces import cohorts

class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        python manage.py faces_cohort 100588
        """
        apr_id_start = int(args[0])
        months = (
            (1, 2014), (2, 2014), (3, 2014), (4, 2014), (5, 2014), (6, 2014),
            (7, 2014), (8, 2014), (9, 2014), (10, 2014), (11, 2014), (12, 2014),
        )
        for batch in months:
            cohorts.full_monthly_cohort_generation(batch[0], batch[1], 
                apr_id_start, True)
            apr_id_start = RegistryEntry.get_max_apr_id()+1