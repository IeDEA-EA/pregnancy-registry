# http://stackoverflow.com/questions/2217488/age-from-birthdate-in-python
def calculate_age(born, eventdate):
    try:
        birthday = born.replace(year=eventdate.year)
    except ValueError: # raised when birth date is February 29 and the current year is not a leap year
        birthday = born.replace(year=today.year, day=born.day-1)
    if birthday > eventdate:
        return eventdate.year - born.year - 1
    else:
        return eventdate.year - born.year


def log_data(entry, message, field_key=None, concept_id=None):
    print message
    entry_log = EntryLog(registry_entry=entry, message=message, 
        field_key=field_key, concept_id=concept_id)
    entry_log.save()