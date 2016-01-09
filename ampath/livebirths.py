import datetime
import json
import logging
from openmrs.models import Encounter, Relationship, Person, Patient, \
    ConceptName, Obs, Concept, ConceptAnswer, ConceptClass, ConceptComplex, \
    ConceptDescription, ConceptMapType, ConceptName, ConceptNameTag, \
    ConceptNameTagMap, ConceptNumeric, ConceptSet
from apr.models import RegistryEntry, ArvTherapy, EntryLog
from apr.utils import calculate_age
from apr import serialize

AMRS_DB = 'amrs_db'
APR_DB = 'default'

logger = logging.getLogger(__name__)

ampath_concepts = {

}

def full_monthly_cohort_generation(month=1, year=2014, apr_starting_id=None, save=True):
    print "Starting %s %s %s" % (month, year, apr_starting_id)
    forms378encs = get378forms(month, year, apr_starting_id, True)


def serialize_entries(year, month, filename):
    entries = RegistryEntry.objects.using(APR_DB).filter(
             voided = 0, site=RegistryEntry.SITE_AMPATH,
             cohort_date__year = year,
             cohort_date__month = month).exclude(apr_id__isnull=True)
    serialize.encode_entry([i for i in entries], filename=filename)

def runSingle378Encounter(encounter_id, apr_id, save_entries=False):
    f378 = Encounter.objects.using(AMRS_DB).get(pk=encounter_id)
    return run378form(f378, apr_id, save_entries)

def log_data(entry, message, field_key=None, concept_id=None):
    print message
    entry_log = EntryLog(registry_entry=entry, message=message, 
        field_key=field_key, concept_id=concept_id)
    entry_log.save()

def run378form(f378, cur_apr_id, save_entries=False):
    logger.info("Starting 378 encounter: %s" % (f378.encounter_id,))
    # If we've already done this specific encounter we should skip it and 
    # move on.
    entry = RegistryEntry()
    if RegistryEntry.objects.filter(child_initial_enc_id=f378.encounter_id).count() > 0:
        logger.info("This encounter id was already processed, skipping and moving on.")
        return entry
    #  1. Encounter ID
    entry.child_initial_enc_id = f378.encounter_id
    #  2. Age in days since encounter
    entry.age_first_seen = age_in_days_at_encounter(f378)
    #  3. Child Patient ID
    entry.child_id = f378.patient_id

    # Has this child been used previously, if so void the encounter.
    duplicate_entries = RegistryEntry.objects.filter(
        site=RegistryEntry.SITE_AMPATH, child_id=entry.child_id)
    if duplicate_entries.count() > 0:
        entry.voided = True
        entry.voided_reason = entry.VOIDED_DUPLICATE_CHILD_ENTRY
        entry.voided_duplicate = True

    child_patient = f378.patient
    #  4. Mom Patient ID
    entry.mother_id = get_linked_mother(f378)
    #  5. Length of Mom's ARV History
    entry.length_of_moms_arv_history = previous_encounters_in_days(
        entry.mother_id, f378.encounter_datetime.date())

    entry.site = RegistryEntry.SITE_AMPATH
    entry.cohort_date = f378.encounter_datetime.date()
    entry.outcome = entry.OUTCOME_LIVE
    entry.date_of_outcome = child_patient.patient.birthdate
    entry.age_first_seen = (entry.cohort_date - entry.date_of_outcome).days
    entry.gender = child_patient.patient.gender

    init_obs = f378.obs_set
    # Birth Defect Noted
    """
    Field: Birth Defect 
    If concept 6246 or 6245 is used, we use that checkbox value.
    If the birth defect checkbox is left blank, then we look to see if any
    of the following concepts are recorded, and if they are we record those
    birth defects:
        8320, 8321, 8322, 8323, 8324, 8325, 8326, 8327, 8328
    aprfield"""
    if init_obs.filter(concept_id=6246, value_coded=6242).count() > 0:
        entry.birth_defect = RegistryEntry.DEFECT_NO
    elif init_obs.filter(concept_id=6245, value_coded=6242).count() > 0:
        entry.birth_defect = RegistryEntry.DEFECT_YES
    else:
        congab_concepts = [8320, 8321, 8322, 8323, 8324, 8325, 8326, 8327, 8328]
        congab_obs = init_obs.filter(concept_id__in = congab_concepts, voided=0)
        if congab_obs.count() > 0:
            entry.birth_defect = RegistryEntry.DEFECT_YES
        else:
            entry.birth_defect = RegistryEntry.DEFECT_UNKNOWN
    # Birth Weight
    weight_obs = init_obs.filter(concept_id=5916)
    if weight_obs.count() > 0:
        entry.birth_weight = weight_obs[0].value_numeric * 1000

    if save_entries:
        entry.save(using=APR_DB)

    if entry.mother_id:
        entry.check_mother_linked = True
        mother = Patient.objects.using(AMRS_DB).get(
                                    patient_id=entry.mother_id)
        # Date First Seen...
        # LMP and/or EDD
        begin_date = entry.date_of_outcome - datetime.timedelta(360)
        log_data(entry, "Beginning date of LMP Search: %s" % (begin_date,), 'lmp')
        lmp_obs = Obs.objects.using(AMRS_DB).filter(
                            concept_id=1836,
                            obs_datetime__gte=begin_date,
                            obs_datetime__lte=entry.date_of_outcome,
                            person_id=entry.mother_id,
                            voided=0,
                         ).order_by('-obs_datetime')
        if lmp_obs.count() > 0:
            entry.lmp = lmp_obs[0].value_datetime
        for lmp in lmp_obs:
            log_data(entry, "Potential LMP Obs/Date: %s , %s" % (lmp.obs_id, lmp.value_datetime), 'lmp', 1836)
        # Age at Conception
        entry.age_at_conception = calculate_age(mother.patient.birthdate,
                            entry.date_of_outcome - datetime.timedelta(days=270))
        # Mother ARVS
        arvset = set_mother_arvs(entry)
        if len(arvset) == 0:
            entry.voided = True
            entry.voided_reason = entry.VOIDED_NO_ARV_HISTORY
            entry.voided_no_arv_history = True
    else:
        entry.check_mother_linked = False
        entry.voided = True
        entry.voided_reason = RegistryEntry.VOIDED_MOTHER_NOT_LINKED
        entry.voided_mother_not_linked = True

    # If we're not voided assign an APR ID
    if entry.voided == False:
        entry.apr_id = cur_apr_id

    if save_entries:
        entry.save(using=APR_DB)

    return entry


def get378forms(month=None, year=2014, apr_starting_id=0, save_entries=False):
    """
    
    """
    cur_apr_id = apr_starting_id
    form378encs = Encounter.objects.using(AMRS_DB).filter(
                    voided=0,
                    form_id=378,
                    encounter_datetime__year=year,
                    encounter_datetime__month=month)
    logger.info("Number of 378 forms: %s" % (form378encs.count(),))
    for f378 in form378encs:
        entry = run378form(f378, cur_apr_id, save_entries)
        print "Do we increment...", entry.voided, " : ", entry.apr_id
        if entry.voided == False and entry.apr_id != None:
            logger.info("Incrementing current apr_id, just used %s" % (cur_apr_id,))
            cur_apr_id += 1

def set_mother_arvs(entry, save_entries=False):
    """
    Look up and set ARV's for mom. Returns a list of new ARV's.
    """
    schemafile = './apr/registry-schema.json'
    with open(schemafile) as f:
        schema = json.loads(f.read())
    arvs = schema['ampath-mapping']['arvs']
    arvset = []
    begin_date = entry.date_of_outcome - datetime.timedelta(360*2)
    log_data(entry, "Beginning date for searching ARVs %s" % (begin_date,), 'arvs', 1088)
    encobs = Obs.objects.using(AMRS_DB).filter(voided=0,
        obs_datetime__gte=begin_date,
        obs_datetime__lte=entry.date_of_outcome,
        person_id=entry.mother_id).order_by('obs_datetime')
    course = 1
    cur_arv = None
    for encob in encobs:
        if encob.concept_id == 1088:
            if encob.value_coded_id != cur_arv:
                cur_arv = encob.value_coded_id
                arvt = ArvTherapy()
                arvt.registry_entry = entry
                arvt.course = course
                arvt.medcode = arvs[str(cur_arv)]['medcode']
                arvt.date_began = encob.obs_datetime.date()
                log_data(entry, "Using ARV %s %s" % (encob.concept_id, encob.obs_datetime,), 'arv', 1088)
                if save_entries:
                    arvt.save(using=APR_DB)
                arvset.append(arvt)
                course += 1
            else:
                log_data(entry, "Skipping cur ARV %s %s" % (encob.concept_id, encob.obs_datetime,), 'arv', 1088)
                pass
    # Go through and adjust the end dates as well as the ongoing flag 
    for idx, arvt in enumerate(arvset):
        if len(arvset) == 1:
            arvt.ongoing = 1
        elif idx == 0:
            arvt.ongoing = 0
            arvt.date_ended = arvset[idx+1].date_began
        elif idx == (len(arvset)-1):
            arvt.ongoing = 1
        else:
            arvt.ongoing = 0
            arvt.date_ended = arvset[idx+1].date_began
        print("Saving the updated status...")
        arvt.save(using=APR_DB)
    return arvset

def previous_encounters_in_days(patient_id, marker_date):
    """
    This will look at the encounters of patient, and find how far back from day
    they have encounters, and return that time as the number of days.

    This is being used to see if we have encounters for the mother during
    pregnancy. So, from the date of birth, we'd like to see that she has at
    least 270 days of previous encounter history so we can look at the ARV's she
    was on during pregnancy.

    Return None is there are no encounters before the marker_date.
    """
    encs = Encounter.objects.using(AMRS_DB).filter(patient_id=patient_id,
                encounter_datetime__lte = marker_date, voided=0).order_by('encounter_datetime')
    if len(encs) == 0:
        return None
    else:
        return (marker_date - encs[0].encounter_datetime.date()).days


def get_linked_mother(encounter=None, patient=None, patient_id=None):
    """
    Using either the provided encounter, patient, or patientID, find a linked
    mother if one exists. Otherwise return None.
    """
    """
    Returns None if we can't find a mom, or if there are too many linked,
    or any other issues arise.
    """
    if encounter:
        child_id = encounter.patient_id
    elif patient:
        child_id = patient.patient_id
    elif patient_id:
        child_id = patient_id
    else:
        raise Error()
    mom = None
    rels = Relationship.objects.using(AMRS_DB).filter(person_b=child_id, voided=0)
    for rel in rels:
        try:
            if rel.relationship.relationship_type_id == 2 and rel.person_a.gender == 'F':
                mom = rel.person_a.person_id
        except Person.DoesNotExist:
            pass
    return mom


def age_in_days_at_encounter(encounter):
    """
    Takes an encounter object and returns the patients age in days when the
    encounter took place. This is used in our process to filter out children who
    were over 3 months old during their initial encounter.
    """
    return (encounter.encounter_datetime.date() - encounter.patient.patient.birthdate).days