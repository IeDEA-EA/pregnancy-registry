"""
Routines to import the cohort for March 2014 that was submitted against the 
old database implementation at INC.
"""
import csv
from apr.models import RegistryEntry

def parse_cohort_csv(filename):
    with open(filename, 'rU') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",", dialect=csv.excel_tab)
        for row in reader:
            print row
            add_patient(row["RegistryID"], row["PatientID"], row["EncounterID"])

def add_patient(reg_id, patient_id, enc_id):
    entry = RegistryEntry()
    entry.site = RegistryEntry.SITE_AMPATH
    entry.child_id = patient_id
    entry.apr_id = reg_id
    entry.child_initial_enc_id = enc_id
    entry.outcome = RegistryEntry.OUTCOME_LIVE
    entry.save(using="apr_db")