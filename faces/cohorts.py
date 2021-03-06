import datetime
import json
import logging
from openmrs.models import Encounter, Relationship, Person, Patient, ConceptName, \
    Concept, ConceptAnswer, ConceptClass, ConceptComplex, ConceptDescription, \
    ConceptMapType, ConceptName, ConceptNameTag, ConceptNameTagMap, \
    ConceptNumeric, ConceptSet, Obs
from apr.models import RegistryEntry, ArvTherapy
from apr.utils import calculate_age
from apr import serialize
from faces import get_mom

FACES_OPENMRS_DB = 'faces_openmrs_db'
APR_DB = 'default'

def full_monthly_cohort_generation(month=1, year=2014, apr_starting_id=None, save=False):
    """
    Standard full method for generating the monthly cohorts that the management
    command will call in to.
    """
    hei_encs = get_hei_encounters(month=month, year=year)
    cur_apr_id = apr_starting_id
    for enc in hei_encs:
        next_entry = process_hei_encounter(enc, cur_apr_id, save=save)
        if next_entry.voided == False and next_entry.apr_id != None:
            #logger.info("Incrementing current apr_id, just used %s" % (cur_apr_id,))
            cur_apr_id += 1
        
    cur_apr_id = RegistryEntry.get_max_apr_id() + 1
    process_nonlive_encounters(month=1, year=2014, apr_starting_id=cur_apr_id, save=save)


def process_nonlive_encounters(month, year, apr_starting_id, save=False):
    """
    This will focus on getting stillborns and/or abortions.

    Concept
    6765 Recently Miscarriaged
    50 Pregnancy Termination
    6848 Stillbirth
    """
    recent_misscarriage = Obs.objects.using(FACES_OPENMRS_DB).filter(voided = 0,
                                        concept_id = 1836, value_coded = 6765,
                                        obs_datetime__year=year,
                                        obs_datetime__month=month,)

    preg_terminated = Obs.objects.using(FACES_OPENMRS_DB).filter(voided = 0,
                                        concept_id = 1836, value_coded = 50,
                                        obs_datetime__year=year,
                                        obs_datetime__month=month,)

    stillbirth = Obs.objects.using(FACES_OPENMRS_DB).filter(voided = 0,
                                        concept_id = 1836, value_coded = 6848,
                                        obs_datetime__year=year,
                                        obs_datetime__month=month,)
    
    cur_apr_id = apr_starting_id
    for ob in recent_misscarriage:
        next_entry = process_nonlive_encounter(RegistryEntry.OUTCOME_ABORTION_SPONT, ob.encounter, cur_apr_id, save=save)
        if next_entry.voided == False and next_entry.apr_id != None:
            cur_apr_id += 1

    for ob in preg_terminated:
        next_entry = process_nonlive_encounter(RegistryEntry.OUTCOME_ABORTION_SPONT, ob.encounter, cur_apr_id, save=save)
        if next_entry.voided == False and next_entry.apr_id != None:
            cur_apr_id += 1

    for ob in stillbirth:
        next_entry = process_nonlive_encounter(RegistryEntry.OUTCOME_STILLBIRTH, ob.encounter, cur_apr_id, save=save)
        if next_entry.voided == False and next_entry.apr_id != None:
            cur_apr_id += 1



def process_nonlive_encounter(outcome_type, enc, cur_apr_id, save=False):
    """
    Encounter is the blue card from when the mother had a marked
    stillborn/miscarriage etc.
    """
    

    entry = RegistryEntry()
    entry.site = RegistryEntry.SITE_FACES
    entry.mother_id = enc.patient_id
    entry.cohort_date = enc.encounter_datetime.date()
    entry.outcome = outcome_type
    entry.date_of_outcome = enc.encounter_datetime.date()

    # If an entry with this mother already exists we will consider it a duplicate,
    # considering that our entire timeline is just under 2 years.
    duplicate_entries = RegistryEntry.objects.filter(
        site=RegistryEntry.SITE_FACES, mother_id=entry.mother_id)
    if duplicate_entries.count() > 0:
        entry.voided = True
        entry.voided_reason = entry.VOIDED_DUPLICATE_CHILD_ENTRY
        if save: entry.save(using=APR_DB)
        return entry

    if save: entry.save(using=APR_DB)
    try:
        add_mother_values_except_arvs(entry)
        add_mother_arvs(entry, save=save)
    except Patient.DoesNotExist:
        entry.voided = True
        entry.voided_reason = RegistryEntry.VOIDED_STILLBIRTH_MOTHER_MISSING
    # If we're not voided assign an APR ID
    if entry.voided == False:
        entry.apr_id = cur_apr_id
    if save: entry.save(using=APR_DB)
    return entry


def process_hei_encounter(enc, apr_id, save=False):
    entry = RegistryEntry()
    entry.site = RegistryEntry.SITE_FACES
    entry.child_id = enc.patient_id
    entry.cohort_date = enc.encounter_datetime.date()
    entry.child_initial_enc_id = enc.encounter_id

    duplicate_entries = RegistryEntry.objects.filter(
        site=RegistryEntry.SITE_FACES, child_id=entry.child_id)
    if duplicate_entries.count() > 0:
        entry.voided = True
        entry.voided_reason = entry.VOIDED_DUPLICATE_CHILD_ENTRY

    # TODO May need to add a check to look at the section titled:
    # FINAL HEI OUTCOMES AT EXIT
    entry.outcome = RegistryEntry.OUTCOME_LIVE
    entry.date_of_outcome = enc.patient.patient.birthdate
    entry.gender = enc.patient.patient.gender

    entry.age_first_seen = (entry.cohort_date - entry.date_of_outcome).days
    # Void entry if they were not seen in the first 3 months
    if entry.age_first_seen > 90:
        entry.voided = True
        entry.voided_reason = RegistryEntry.VOIDED_TOO_OLD_AT_PAEDS_ENC
    if save: entry.save(using=APR_DB)
    mom = get_mom(entry.child_id)
    if mom != None:
        entry.mother_id = mom
    else:
        entry.voided = True
        entry.voided_reason = RegistryEntry.VOIDED_MOTHER_NOT_LINKED
        if save: entry.save(using=APR_DB)
        return entry
    if save: entry.save(using=APR_DB)
    add_mother_values_except_arvs(entry)
    if save: entry.save(using=APR_DB)
    add_mother_arvs(entry, save=save)
    add_child_values(entry)
    # If we're not voided assign an APR ID
    if entry.voided == False:
        entry.apr_id = apr_id
    if save: entry.save(using=APR_DB)
    return entry


def add_child_values(entry):
    """
    Goes through the child hei form obs and fills in the fields specific to:
    - birth defect
    - birth weight
    - length: TODO Need to ask Taylor about this post dated value. On my TODO
      list
    - head circumference (This actually isn't collected at FACES so we can't
      include it.)
    """
    child_obs = Obs.objects.using(FACES_OPENMRS_DB).filter(
        person_id=entry.child_id,
        voided=0,
        encounter_id=entry.child_initial_enc_id
    )
    try:
        encob = child_obs.get(concept_id=5547)
        if encob.value_coded == 1065:
            entry.birth_defect = RegistryEntry.DEFECT_YES
        elif encob.value_coded == 1066:
            entry.birth_defect = RegistryEntry.DEFECT_NO
        else:
            entry.birth_defect = RegistryEntry.DEFECT_UNKNOWN
    except Obs.DoesNotExist:
        entry.birth_defect = RegistryEntry.DEFECT_UNKNOWN
    except Obs.MultipleObjectsReturned:
        # TODO
        pass 
    try:
        encob = child_obs.get(concept_id=5916)
        entry.birth_weight = encob.value_numeric * 1000
    except Obs.DoesNotExist:
        pass
    print "Birth Weight: ", entry.birth_weight

def add_mother_arvs(entry, save=False):
    schemafile = './apr/registry-schema.json'
    with open(schemafile) as f:
        schema = json.loads(f.read())
    arvs = schema['faces-mapping']['arvs']
    begin_date = entry.date_of_outcome - datetime.timedelta(540)
    preg_encobs = Obs.objects.using(FACES_OPENMRS_DB).filter(
        person_id=entry.mother_id,
        voided=0,
        obs_datetime__gte=begin_date,
        obs_datetime__lte=entry.date_of_outcome).order_by('obs_datetime')

    # arvs
    course = 1
    cur_arv = None
    arvs_obs = preg_encobs.filter(concept_id=1571)
    if arvs_obs.count() == 0:
        entry.voided_reason = RegistryEntry.VOIDED_NO_ARV_HISTORY
        entry.voided = True
        if save: entry.save()
    for arv in arvs_obs:
        if arv.value_coded != cur_arv:
            cur_arv = arv.value_coded_id
            arvt = ArvTherapy()
            arvt.registry_entry = entry
            arvt.course = course
            #print "The cur_arv is: ", cur_arv, " ", str(cur_arv)
            arvt.medcode = arvs[str(cur_arv)]['medcode']
            arvt.date_began = arv.obs_datetime
            if save: arvt.save(using=APR_DB)
            #print 'c: ', course, ' medcode: ', arvs[str(cur_arv)]['medcode'], ' datestarted: ', arv.obs_datetime
            course += 1
        else:
            pass
    

def add_mother_values_except_arvs(entry):
    """
    This will take care of all of moms values except for her ARV regimens.
    - date_first_seen
    - lmp and/or edd
    - age_at_conception
    """
    begin_date = entry.date_of_outcome - datetime.timedelta(360)
    preg_encobs = Obs.objects.using(FACES_OPENMRS_DB).filter(
        person_id=entry.mother_id,
        voided=0,
        obs_datetime__gte=begin_date,
        obs_datetime__lte=entry.date_of_outcome).order_by('obs_datetime')

    # Date First Seen
    dates_first_seen = preg_encobs.filter(concept_id=1836, value_coded=1065)
    #print "How Many Date First Seens: ", len(dates_first_seen)
    for seen in dates_first_seen:
        #print "    ", seen.value, "    ", seen.obs_datetime
        entry.date_first_seen = seen.obs_datetime
        break
    
    # 1450 LAST MONTHLY PERIOD DATE
    lmps = preg_encobs.filter(concept_id=1450)
    #print "Number LMPS: ", len(lmps)
    for lmp in lmps:
        entry.lmp = lmp.value
        break
    # 1451 EXPECTED DELIVERY DATE
    edds = preg_encobs.filter(concept_id=1451)
    #print "Number EDDS: ", len(edds)
    for edd in edds:
        entry.edd = edd.value
        break

    # age at conception
    mother_patient = Patient.objects.using(FACES_OPENMRS_DB).get(pk=entry.mother_id)
    print "EntryID: ", entry.id, "Motherbirthdate: ", mother_patient.patient.birthdate, " Date first seen: ", entry.date_first_seen
    if entry.date_first_seen:
        print type(mother_patient.patient.birthdate)
        print type(entry.date_first_seen)
        entry.age_at_conception = calculate_age(mother_patient.patient.birthdate,
                                        entry.date_first_seen.date())
    elif entry.lmp:
        entry.age_at_conception = calculate_age(mother_patient.patient.birthdate,
                                        entry.lmp)
    else:
        # Use the outcome if we absolutely have to
        entry.age_at_conception = calculate_age(mother_patient.patient.birthdate,
                                        entry.date_of_outcome)
    print "Age: ", entry.age_at_conception


def get_hei_encounters(month, year):
    """
    The HEI Encounters are currently based off of this SQL lookup. This should
    be reviewed from time to time in case any of the sites or forms/encounter
    types change.

        select * from encounter where
        encounter_datetime >= "2014-01-01" and
        location_id in (2,57,4,6,5,7,13,16,28) and
        voided = 0 and
        encounter_type = 26;

    FACES_AUDIT"""
    cohort = Encounter.objects.using(FACES_OPENMRS_DB).filter(
        voided=0,
        encounter_type=26,
        encounter_datetime__year=year,
        encounter_datetime__month=month,
        location_id__in=(2,57,4,6,5,7,13,16,28)
    )
    return [c for c in cohort]