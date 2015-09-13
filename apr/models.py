from django.db import models

class TimestampedModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class RegistryEntry(TimestampedModel):
    SITE_AMPATH = "AMPATH"
    SITE_FACES = "FACES"

    SITE_CHOICES = (
        (SITE_AMPATH, "AMPATH"),
        (SITE_FACES, "FACES"),
    )
    site = models.CharField(max_length=25, choices=SITE_CHOICES)
    # These are the original OpenMRS ID's from either AMRS or FACESOpenMRS
    mother_id = models.IntegerField(blank=True, null=True)
    child_id = models.IntegerField(blank=True, null=True)
    # The ID of the initial encounter... forms differ between Ampath and FACES,
    # but in each case there is still a single form for the child starting out.
    child_initial_enc_id = models.IntegerField(blank=True, null=True)
    # Need a strategy for dealing with twins in this instance
    apr_id = models.IntegerField(null=True, blank=True, unique=True)
    # This is the date of the encounter_id that defines this entry. Could be
    # from the Paeds Initial Encounter, or from a mother form that indicates
    # stillbirth.
    cohort_date = models.DateField(blank=True, null=True)
    # Age in days when the paeds initial encounter took place
    age_first_seen = models.IntegerField(blank=True, null=True)
    # One-to-many motherobs_set
    # One-to-many childobs_set

    # Registration Form Items
    date_first_seen = models.DateField(blank=True, null=True)
    lmp = models.DateField(blank=True, null=True)
    edd = models.DateField(blank=True, null=True)
    age_at_conception = models.IntegerField(blank=True, null=True)
    # One-to-many arvtherapy_set

    # Follow-up Form
    DEFECT_NO = 0
    DEFECT_YES = 1
    DEFECT_UNKNOWN = 2
    DEFECT_FLAG = 42
    DEFECT_CHOICES = (
        (DEFECT_NO, "No"),
        (DEFECT_YES, "Yes"),
        (DEFECT_UNKNOWN, "Unknown"),
        (DEFECT_FLAG, "Flagged"), # Unexpected findings, flag and check manually
    )
    birth_defect = models.IntegerField(blank=True, null=True, choices=DEFECT_CHOICES)
    OUTCOME_LIVE = 1
    OUTCOME_ABORTION_SPONT = 2
    OUTCOME_ABORTION_INDUC = 3
    OUTCOME_STILLBIRTH = 4
    OUTCOME_UNKNOWN = 5
    OUTCOME_CHOICES = (
        (OUTCOME_LIVE, "Live Infant"),
        (OUTCOME_ABORTION_SPONT, "Abortion, Spontaneous"),
        (OUTCOME_ABORTION_INDUC, "Abortion, Induced"),
        (OUTCOME_STILLBIRTH, "Stillbirth"),
        (OUTCOME_UNKNOWN, "Unknown"),
    )
    outcome = models.IntegerField(blank=True, choices=OUTCOME_CHOICES)
    # This is the APR Baby ID
    baby_id = models.CharField(max_length=255, blank=True)
    date_of_outcome = models.DateField(blank=True, null=True)
    gestational_age = models.IntegerField(blank=True, null=True) # In weeks
    GENDER_FEMALE = 'F'
    GENDER_MALE = 'M'
    GENDER_CHOICES = (
        (GENDER_FEMALE, "Female"),
        (GENDER_MALE, "Male"),
    )
    gender = models.CharField(max_length=1, blank=True, choices=GENDER_CHOICES)
    birth_weight = models.DecimalField(blank=True, max_digits=10, decimal_places=2, null=True)
    length = models.DecimalField(blank=True, max_digits=7, decimal_places=2, null=True)
    head_circ = models.DecimalField(blank=True, max_digits=7, decimal_places=2, null=True)
    # One-to-many birthdefects_set
    # One-to-many fetalloss_set

    voided = models.BooleanField(default=False)
    VOIDED_TOO_OLD_AT_PAEDS_ENC = "VOIDED_TOO_OLD_AT_PAEDS_ENC"
    VOIDED_MOTHER_NOT_LINKED = "VOIDED_MOTHER_NOT_LINKED"
    VOIDED_STILLBIRTH_MOTHER_MISSING = "VOIDED_STILLBIRTH_MOTHER_MISSING"
    VOIDED_NO_ARV_HISTORY = "VOIDED_NO_ARV_HISTORY"
    VOIDED_DUPLICATE_CHILD_ENTRY = "VOIDED_DUPLICATE_CHILD_ENTRY"
    CHOICES_VOIDED_REASON = (
        (VOIDED_TOO_OLD_AT_PAEDS_ENC, "Child too old at Paeds Initial Encounter"),
        (VOIDED_MOTHER_NOT_LINKED, "Mother not linked"),
        (VOIDED_STILLBIRTH_MOTHER_MISSING, "Mother Patient record for stillbirth missing"),
        (VOIDED_NO_ARV_HISTORY, "No ARV History for Mother"),
        (VOIDED_DUPLICATE_CHILD_ENTRY, "Duplicate Child Entry")
    )
    voided_reason = models.CharField(max_length=255, choices=CHOICES_VOIDED_REASON)

    # So we can have multiple voided reasons
    voided_duplicate = models.BooleanField(default=False)
    voided_too_old_at_paeds_encounter = models.BooleanField(default=False)
    voided_mother_not_linked = models.BooleanField(default=False)
    voided_no_arv_history = models.BooleanField(default=False)

    # Book Keeping Below
    # Checks for live outcome
    #check_initial_paeds_lookup = models.BooleanField(default=False)
    #check_mother_linked = models.BooleanField(default=False)
    #check_for_defects = models.BooleanField(default=False)
    #check_added_child_obs = models.BooleanField(default=False)

    # Checks for stillbirth
    #check_initial_stillbirth_enc = models.BooleanField(default=False)
    #check_fetal_loss_issues = models.BooleanField(default=False)

    # Checks for either case
    #check_calc_age_first_seen = models.BooleanField(default=False)
    #check_history_length_moms_obs = models.BooleanField(default=False)
    #check_lmp_edd = models.BooleanField(default=False)
    #check_generate_moms_arvs = models.BooleanField(default=False)
    #check_added_moms_obs = models.BooleanField(default=False)

    status = models.CharField(max_length=100)
    # One-to-many notes_set

    #class Meta:
    #   Maybe site and child_id should be unique...
    #    unique_together = (("sit"))

    @classmethod
    def get_max_apr_id(cls):
        return cls.objects.aggregate(models.Max('apr_id'))['apr_id__max']

class ArvTherapy(TimestampedModel):
    registry_entry = models.ForeignKey(RegistryEntry)
    course = models.IntegerField()
    medcode = models.CharField(max_length=255)
    total_daily_dose = models.IntegerField(blank=True, null=True)
    taking_at_conception = models.IntegerField(blank=True, null=True)
    date_began = models.DateField()
    date_ended = models.DateField(blank=True, null=True)
    ongoing = models.IntegerField(blank=True, null=True)


class BirthDefects(TimestampedModel):
    registry_entry = models.ForeignKey(RegistryEntry)
    defect = models.CharField(max_length=255)
    attributed_to_arv = models.IntegerField(blank=True)
    other_factors = models.CharField(blank=True, max_length=255)


class FetalLoss(TimestampedModel):
    registry_entry = models.ForeignKey(RegistryEntry)
    factors = models.CharField(blank=True, max_length=255)


class EncObs(models.Model):
    patient_id = models.IntegerField(null=True, blank=True)
    # Only one of these should be used ideally
    mother_entry = models.ForeignKey(RegistryEntry, related_name="motherobs", null=True, blank=True)
    child_entry = models.ForeignKey(RegistryEntry, related_name="childobs", null=True, blank=True)

    # Encounter fields
    encounter_id = models.IntegerField(null=True, blank=True)
    encounter_type = models.IntegerField(null=True, blank=True)
    location_id = models.IntegerField(null=True, blank=True)
    form_id = models.IntegerField(null=True, blank=True)
    encounter_datetime = models.DateTimeField()
    voided = models.IntegerField()

    # Obs Fields
    obs_id = models.IntegerField()
    concept_id = models.IntegerField(null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)
    obs_datetime = models.DateTimeField()
    #location = models.IntegerField(null=True, blank=True)
    obs_group_id  = models.IntegerField(null=True, blank=True)
    value_group_id = models.IntegerField(null=True, blank=True)
    value_boolean = models.IntegerField(null=True, blank=True)
    value_coded = models.IntegerField(blank=True, null=True)
    value_coded_name_id = models.IntegerField(blank=True, null=True)
    value_drug = models.IntegerField(blank=True, null=True)
    value_datetime = models.DateTimeField(null=True, blank=True)
    value_numeric = models.FloatField(null=True, blank=True)
    value_modifier = models.CharField(max_length=6, blank=True, null=True)
    value_text = models.TextField(blank=True, null=True)
    comments = models.CharField(max_length=765, blank=True, null=True)
    date_created = models.DateTimeField(blank=True, null=True)
    obs_voided = models.IntegerField()
    value_complex = models.CharField(max_length=765, blank=True, null=True)

    # For readability
    concept_name = models.CharField(max_length=255, blank=True, null=True)

    @property
    def value(self):
        if self.value_numeric:
            return self.value_numeric
        elif self.value_datetime:
            return self.value_datetime.date()
        elif self.value_boolean:
            return self.value_boolean
        elif self.value_coded:
            return self.value_coded.concept_id
        elif self.value_text:
            return self.value_text
        else:
            return None
            raise NotImplementedError("ObsId: " + str(self.obs_id) + " " \
                    + str(self.concept_id))


class Notes(TimestampedModel):
    registry_entry = models.ForeignKey(RegistryEntry)
    text = models.TextField(blank=True)
    note_type = models.CharField(max_length=50, blank=True)
