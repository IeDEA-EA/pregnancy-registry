from django.test import TestCase
from ampath import livebirths
from django.db import connections
from pregreg.secure import ALL_DATABASES
from django.db import transaction

class AmpathTests(TestCase):
    
    def setUp(self):
        """
        We don't want to create the extra openmrs database in our test set.
        """
        connections.databases['amrs_db'] = ALL_DATABASES['amrs_db']

    def test_medcodekey_issue(self):
        livebirths.runSingle378Encounter(5465678, 1, False)
        transaction.rollback()

    # def test_full_run_checks(self):
    #     for i in range(1,13):
    #         livebirths.full_monthly_cohort_generation(month=i, year=2015, save=True)