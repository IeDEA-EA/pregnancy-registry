from django.test import TestCase
from faces import cohorts
from django.db import connections
from pregreg.secure import ALL_DATABASES

class FacesTest(TestCase):
    
    def setUp(self):
        """
        We don't want to create the extra openmrs database in our test set.
        """
        connections.databases['faces_openmrs_db'] = ALL_DATABASES['faces_openmrs_db']

    def test_hei_size(self):
        self.assertEqual(len(cohorts.get_hei_encounters(1,2014)),155)

    def test_full_run_checks(self):
        for i in range(1,13):
            cohorts.full_monthly_cohort_generation(month=i, year=2014, save=False)