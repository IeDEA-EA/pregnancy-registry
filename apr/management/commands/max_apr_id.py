from django.core.management.base import BaseCommand, CommandError
from apr.models import RegistryEntry

class Command(BaseCommand):
    """
    Prints the largest APR Registry ID that has been used so far. 
    """

    def handle(self, *args, **options):
        print RegistryEntry.get_max_apr_id()