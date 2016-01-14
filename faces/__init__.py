"""
FACES APR Cohort and Definition Routines.
"""
import datetime
import json
from openmrs.models import Encounter, Relationship, Person, Patient, ConceptName, Obs
from apr.models import RegistryEntry, EncObs, ArvTherapy
from apr import utils as emrutils

FACES_OPENMRS_DB = 'faces_openmrs_db'
APR_DB = 'apr_db'

def build_stage_1():
    """
    In stage 1 of generation we:
    1. Get the initial HEI Encounters
    2. Create a RegistryEntry for each one
    3. Calculate the age of the child at HEI presentation for each one
    4. Check if the mother is linked
    5. Add the obs for the HEI initial encounter

    Essentially, we do anything we can that's on the HEI form (except maybe
    format the actual defects in the event that there are some). Also, we see
    if we can link the mom.
    """
    # 1
    hei_enc = get_hei_encounters()
    # 2
    for enc in hei_enc:
        entry = RegistryEntry()
        entry.site = RegistryEntry.SITE_FACES
        entry.child_id = enc.patient_id
        entry.cohort_date = enc.encounter_datetime.date()
        # TODO May need to add a check to look at the section titled:
        # FINAL HEI OUTCOMES AT EXIT
        entry.outcome = RegistryEntry.OUTCOME_LIVE
        entry.date_of_outcome = enc.patient.patient.birthdate
        entry.gender = enc.patient.patient.gender
        entry.check_initial_paeds_lookup = True
        # 3
        entry.age_first_seen = (entry.cohort_date - entry.date_of_outcome).days
        # 4
        entry.save(using=APR_DB)
        mom = get_mom(entry.child_id)
        if mom != None:
            entry.mother_id = mom
            entry.check_mother_linked = True
            mom_patient = Patient.objects.using(FACES_OPENMRS_DB).get(pk=entry.mother_id)
            for mom_enc in mom_patient.encounter_set.all():
                encounter_to_encobs(entry, mom_enc, link_field='mother_entry')
            entry.check_added_moms_obs = True
        else:
            entry.voided = True
            entry.voided_reason = RegistryEntry.VOIDED_MOTHER_NOT_LINKED
        entry.save(using=APR_DB)
        set_mother_values(entry)
        # 5
        encounter_to_encobs(entry, enc)
        entry.check_added_child_obs = True
        set_child_values(entry)
        entry.save(using=APR_DB)


def build_stage_2():
    """
    Currently contains:
    set_mother_arvs
    """
    faces_entries = RegistryEntry.objects.using(APR_DB).filter(site=RegistryEntry.SITE_FACES)
    for entry in faces_entries:
        set_mother_values(entry)


def set_non_livebirth_entry(outcome_type, enc):
    """
    Encounter is the blue card from when the mother had a marked
    stillborn/miscarriage etc.
    """
    entry = RegistryEntry()
    entry.site = RegistryEntry.SITE_FACES
    entry.cohort_date = enc.encounter_datetime.date()
    entry.outcome = outcome_type
    entry.date_of_outcome = enc.encounter_datetime.date()
    entry.save(using=APR_DB)
    for mom_enc in enc.patient.encounter_set.all():
        encounter_to_encobs(entry, mom_enc, link_field='mother_entry')
    entry.check_added_moms_obs = True
    try:
        set_mother_values(entry)
    except Patient.DoesNotExist:
        entry.voided = True
        entry.voided_reason = RegistryEntry.VOIDED_STILLBIRTH_MOTHER_MISSING
    entry.save(using=APR_DB)


def build_stage_3():
    """
    This will focus on getting stillborns and/or abortions.

    1. Get the encounters/mother ids from looking up stillbirth obs.
    2. Create a Registry Entry for each one.
    3. Add the obs for the mother.
    4.

    Concept
    6765 Recently Miscarriaged
    50 Pregnancy Termination
    6848 Stillbirth
    """
    recent_misscarriage = Obs.objects.using(FACES_OPENMRS_DB).filter(voided = 0,
                                        concept_id = 1836, value_coded = 6765)

    preg_terminated = Obs.objects.using(FACES_OPENMRS_DB).filter(voided = 0,
                                        concept_id = 1836, value_coded = 50)

    stillbirth = Obs.objects.using(FACES_OPENMRS_DB).filter(voided = 0,
                                        concept_id = 1836, value_coded = 6848)

    print "recent_misscarriage: ", recent_misscarriage.count()
    print "preg_terminated: ", preg_terminated.count()
    print "stillbirth: ", stillbirth.count()
    total = recent_misscarriage.count() + preg_terminated.count() + stillbirth.count()
    print "total: ", total

    mom_ids = set()
    for i in [recent_misscarriage, preg_terminated, stillbirth]:
        for j in i:
            mom_ids.add(j.person_id)

    print "set total: ", len(mom_ids)

    for ob in recent_misscarriage:
        set_non_livebirth_entry(RegistryEntry.OUTCOME_ABORTION_SPONT, ob.encounter)

    for ob in preg_terminated:
        set_non_livebirth_entry(RegistryEntry.OUTCOME_ABORTION_SPONT, ob.encounter)

    for ob in stillbirth:
        set_non_livebirth_entry(RegistryEntry.OUTCOME_STILLBIRTH, ob.encounter)

    print "Done"


def build_stage_4():
    """
    Don't forget to assign ARV's... that's not part of any of these build steps yet

    If the ARV history is zero, void the entry
    """
    # Quick audit to make sure we have enough ARV history
    faces = RegistryEntry.objects.using(APR_DB).filter(voided=0,
                site=RegistryEntry.SITE_FACES)

    for entry in faces:
        # If someone has *NO* ARV history we will void them
        if entry.arvtherapy_set.count() == 0:
            entry.voided = 1
            entry.voided_reason = RegistryEntry.VOIDED_NO_ARV_HISTORY
            entry.save()

def assign_apr_numbers(year,month,starting_id):
    faces = RegistryEntry.objects.using(APR_DB).filter(voided=0,
                site=RegistryEntry.SITE_FACES,
                cohort_date__month = month,
                cohort_date__year = year)
    cur = starting_id
    for entry in faces:
        entry.apr_id = cur
        entry.save()
        print "Assigned: ", cur
        cur += 1

def build_stage_last_reports():
    from apr.serialize import encode_entry
    aprids_to_encode = []
    for month in [1,5,6,7,8,9,10,11]:
        faces = RegistryEntry.objects.using(APR_DB).filter(voided=0,
                    site=RegistryEntry.SITE_FACES,
                    cohort_date__month = month)
        for entry in faces:
            if entry.apr_id == None:
                # TODO? WHAT??
                continue
            aprids_to_encode.append(entry.apr_id)
        #print "Month: ", month, " unvoided: ", faces.count()
    print "Num to Encode: ", len(aprids_to_encode)
    encode_entry(aprids_to_encode, filename="2015-04-03-FACES-2014-1_5-11.txt")

def set_child_values(entry):
    """
    Goes through the child hei form obs and fills in the fields specific to:
    - birth defect
    - birth weight
    - length: TODO Need to ask Taylor about this post dated value. On my TODO
      list
    - head circumference (This actually isn't collected at FACES so we can't
      include it.)
    """
    # Birth Defect
    try:
        encob = entry.childobs.get(concept_id=5547)
        if encob.value_coded == 1065:
            entry.birth_defect = RegistryEntry.DEFECT_YES
        elif encob.value_coded == 1066:
            entry.birth_defect = RegistryEntry.DEFECT_NO
        else:
            entry.birth_defect = RegistryEntry.DEFECT_UNKNOWN
    except EncObs.DoesNotExist:
        entry.birth_defect = RegistryEntry.DEFECT_UNKNOWN
    except EncObs.MultipleObjectsReturned:
        entry.birth_defect = RegistryEntry.DEFECT_FLAG
    # Birth weight
    try:
        encob = entry.childobs.get(concept_id=5916)
        entry.birth_weight = encob.value_numeric * 1000
    except EncObs.DoesNotExist:
        pass

def set_mother_values(entry):
    """
    This will take care of all of moms values except for her ARV regimens.
    - date_first_seen
    - lmp and/or edd
    - age_at_conception
    """
    begin_date = entry.date_of_outcome - datetime.timedelta(360)
    preg_encobs = entry.motherobs.filter(voided=0,
        encounter_datetime__gte=begin_date,
        encounter_datetime__lte=entry.date_of_outcome).order_by('encounter_datetime')
    for encob in preg_encobs:
        if encob.concept_id == 1836 and encob.value_coded == 1065:
            entry.date_first_seen = encob.encounter_datetime.date()
    # Skip the rest if date_first_seen wasn't available.
    if entry.date_first_seen == None:
        return
    preg_encobs = entry.motherobs.filter(voided=0,
        encounter_datetime__gte=entry.date_first_seen,
        encounter_datetime__lte=entry.date_of_outcome).order_by('encounter_datetime')
    for encob in preg_encobs:
        if entry.lmp == None and encob.concept_id == 1450:
            #entry.lmp = encob.value_datetime
            # TODO I believe faces really only uses LMP For this.
            pass
        elif entry.edd == None and encob.concept_id == 1451:
            entry.edd = encob.value_datetime
    # age_at_conception
    mother_patient = Patient.objects.using(FACES_OPENMRS_DB).get(pk=entry.mother_id)
    print "EntryID: ", entry.id, "Motherbirthdate: ", mother_patient.patient.birthdate, " Date first seen: ", entry.date_first_seen
    entry.age_at_conception = emrutils.calculate_age(mother_patient.patient.birthdate,
                                        entry.date_first_seen)
    print "Age: ", entry.age_at_conception
    entry.save(using=APR_DB)

def generate_all_moms_arvs():
    faces_moms = RegistryEntry.objects.using(APR_DB).exclude(voided=1).filter(site=RegistryEntry.SITE_FACES)
    print "Starting to set entries"
    for entry in faces_moms:
        set_mother_arvs(entry)
    print "Done setting entries"

def set_mother_arvs(entry):
    """
    Look up and set ARV's for mom.
    """
    schemafile = './apr/registry-schema.json'
    with open(schemafile) as f:
        schema = json.loads(f.read())
    arvs = schema['faces-mapping']['arvs']
    arvset = []
    begin_date = entry.date_of_outcome - datetime.timedelta(360*2)
    encobs = entry.motherobs.filter(voided=0,
        encounter_datetime__gte=begin_date,
        encounter_datetime__lte=entry.date_of_outcome).order_by('encounter_datetime')
    course = 1
    cur_arv = None
    for encob in encobs:
        if encob.concept_id == 1571:
            #arvset.add(encob.value_coded)
            if encob.value_coded != cur_arv:
                cur_arv = encob.value_coded
                arvt = ArvTherapy()
                arvt.registry_entry = entry
                arvt.course = course
                arvt.medcode = arvs[str(cur_arv)]['medcode']
                arvt.date_began = encob.encounter_datetime.date()
                arvt.save(using=APR_DB)
                print 'c: ', course, ' medcode: ', arvs[str(cur_arv)]['medcode'], ' datestarted: ', encob.encounter_datetime
                course += 1
            else:
                pass
            print encob.encounter_datetime, encob.value_coded


def encounter_to_encobs(entry, enc, link_field='child_entry'):
    """
    Takes a full openmrs encounter, collects it's obs, turnes them in to internal
    apr EncObs and returns the list of them.
    """
    encobs = []
    for ob in enc.obs_set.all():
        encob = EncObs()
        encob.patient_id = enc.patient.patient.person_id
        # Copy Encounter Fields
        for f in ['encounter_id', 'location_id', 'form_id',
            'encounter_datetime', 'voided']:
            setattr(encob, f, getattr(enc, f))
        encob.encounter_type = enc.encounter_type.encounter_type_id
        # Copy Obs Fields
        for f in ['obs_id', 'concept_id', 'obs_datetime', 'obs_group_id',
            'value_group_id', 'value_boolean', 'value_coded', 'value_coded_name_id',
            'value_drug', 'value_datetime', 'value_numeric', 'value_modifier',
            'value_text', 'comments', 'date_created', 'value_complex']:
            setattr(encob, f, getattr(ob, f))
        encob.obs_voided = ob.voided
        encob.concept_name = ConceptName.objects.using(FACES_OPENMRS_DB).filter(concept_id=ob.concept_id,
                                                        voided=0)[0].name
        setattr(encob, link_field, entry)
        encob.save(using=APR_DB)
        encobs.append(ob)
    return encobs


def get_mom(child_id):
    """
    Returns None if we can't find a mom, or if there are too many linked,
    or any other issues arise.
    """
    mom = None
    rels = Relationship.objects.using(FACES_OPENMRS_DB).filter(person_b=child_id, voided=0)
    for rel in rels:
        try:
            if rel.relationship.relationship_type_id == 3 and rel.person_a.gender == 'F':
                mom = rel.person_a.person_id
        except Person.DoesNotExist:
            pass
    return mom
