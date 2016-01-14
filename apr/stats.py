"""
Generate the statistics for a given month of APR records including:
    - total cohort size
    - number of congenital abnormalites
    - number of entries that were removed from final cohort for any number of
      reasons such as missing mothers, lack of arv information etc.
"""
from django.db import connections
from collections import defaultdict
from apr.models import RegistryEntry

def generate_stats(year, month, site, db='default'):
    cohort_size = RegistryEntry.objects.using(db).filter(
        cohort_date__month=month, 
        cohort_date__year=year, 
        site=site,
        voided=0).count()
    birth_defect = RegistryEntry.objects.using(db).filter(
        cohort_date__month=month, 
        cohort_date__year=year, 
        site=site,
        voided=0).count()
    voided_entries = RegistryEntry.objects.using(db).filter(
        cohort_date__month=month, 
        cohort_date__year=year, 
        site=site,
        voided=1).all()
    voided_reason_counts = defaultdict(int)
    for voided_entry in voided_entries:
        voided_reason_counts[voided_entry.get_voided_reason_display()] += 1
    cohort_entries = RegistryEntry.objects.using(db).filter(
        cohort_date__month=month,
        cohort_date__year=year,
        site=site,
        voided=0).all()
    outcome_counts = defaultdict(int)
    congenital_ab_count = 0
    for cohort_entry in cohort_entries:
        outcome_counts[cohort_entry.get_outcome_display()] += 1
        if cohort_entry.birth_defect == 1: congenital_ab_count += 1

    return {
        "cohort_size": cohort_size,
        "congenital_ab_count": congenital_ab_count,
        "voided_reason_counts": voided_reason_counts,
        "outcome_counts": outcome_counts,
    }
