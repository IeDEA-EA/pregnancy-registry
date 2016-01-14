"""
Generate the statistics for a given month of APR records including:
    - total cohort size
    - number of congenital abnormalites
    - number of entries that were removed from final cohort for any number of
      reasons such as missing mothers, lack of arv information etc.
"""
from django.core.management.base import BaseCommand, CommandError
from apr import stats



class Command(BaseCommand):
    def handle(self, *args, **options):
        site = args[0]
        year = int(args[1])
        for i in range(1,13):
            results = stats.generate_stats(year,i,site=site)
            self.format_results(year, i, site, results)
            print ""

    def format_results(self, year, month, site, results):
            print "Site: %s Year/Mon: %s/%s" % (site, year, month)
            print "Cohort Size: %s Num Congenital Abnormalities: %s" % (
                results['cohort_size'], results['congenital_ab_count'])
            print "Numbers Voided by Cause:"
            for key, val in results['voided_reason_counts'].iteritems():
                print "    %s: %s" % (key,val)
            print "Outcomes:"
            for key, val in results['outcome_counts'].iteritems():
                print "    %s: %s" % (key,val)