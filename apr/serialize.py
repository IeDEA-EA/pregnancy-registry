import datetime
import json
from .models import RegistryEntry

def encode_entry(entry, filename=None, timestamp=None):
    """
    Entry can be a single item or list of either RegistryEntry instances or
    APR ID's. Optional filename will write the data to a file as well as return
    it.
    """
    togo = ''
    re = RegistryEncoder(timestamp=timestamp)
    if type(entry) not in [tuple, list]:
        entry = [entry]
    for e in entry:
        if type(e) == RegistryEntry:
            togo += re.serialize_entry(e) + "\n"
        else:
            togo += re.serialize_entry(RegistryEntry.objects.using('apr_db').get(apr_id=e)) + "\n"
    if filename:
        f = open(filename, 'w')
        f.write(togo)
        f.close()
    return togo

class RegistryEncoder(object):
    def __init__(self, schemafile=None, timestamp=None):
        if schemafile == None:
            schemafile = './apr/registry-schema.json'
        with open(schemafile) as f:
            self.schema = json.loads(f.read())
        self.oc = self.schema['oc-schema']
        self.apr_map = self.schema['apr-model-mapping']
        if not timestamp:
            # Always using Jan 01, 2015, to get around issue they have with
            #reloading database. datetime.date.today().strftime('%Y%m%d'),
            #datetime.date(2015, 1, 1).strftime('%Y%m%d'),
            self.timestamp = datetime.date(2015, 1, 1).strftime('%Y%m%d')
        else:
            self.timestamp = timestamp

    def serialize_entry(self, entry):
        """
        The reg_id is essentially the patient_id but for the registry.
        We need to keep a mapping of these to look them up in the future.
        """
        lines = self._encode(entry)
        return self._serialize_lines(lines)

    def _encode(self, entry):
        """
        Build the field lists that can later be pipe delimited.

        Example: regenc.encode(regEntry, 'ampath-mapping')
        """
        if entry.site == entry.SITE_AMPATH:
            site_mapping = self.schema['ampath-mapping']
        elif entry.site == entry.SITE_FACES:
            site_mapping = self.schema['faces-mapping']
        else:
            raise Error("Unknown site")
        lines = []
        """
        Currently fields look like either the simple list, or dictionary for
        repeating fields:

        "101_P78_SUBMITTED_BY": ["CRF PAGES", "REGISTRATION_FORM", "SUB", "SUB1", "SUB", "SUBBY", 101],

        "3_BLITERAP": {
            "repeat": 5,
            "fields": ["CRF PAGES", "ANTIVIRAL_THERAPY_DURING_PREGN", "ATDP", "ATDP1", "ATDPR", "BLITERAP", 3]
        },
        """

        # arv_page_fields = ["3_BLITERAP", "3_P7_COURSE", "3_P14_STOP_DATE", "3_P16_ONGOING", "3_P13_START_DATE",
        #     "3_P17_EARLIEST_TRIMESTER", "3_P15_STOP_AGE", "3_P13_START_AGE", "3_P5_STOP_DATE_LMP_OR_EDD", 
        #     "3_ATDP_DOMAIN", "3_P6_MEDCODE", "3_P10_ROUTE", "3_P11_MED_AT_CONCEPT", "3_P8_DAILY_DOSE",
        #     "3_P9_UNIT", "3_P3_HCP_OR_SPONSOR", ]

        for field_name, field in self.oc.iteritems():
            if field_name.startswith("3_"):
                continue
            if type(field) == list:
                value = self._field_value(field_name, entry)
                lines.append(self._build_line(field, entry.apr_id,
                            site_mapping['site_id'], site_mapping['study_id'],
                            value=value))
            else:
                #TODO Values for repeating fields
                #arvs = entry.arvtherapy_set.all()
                if field_name.startswith("3_"):   # in ('3_P7_COURSE', '3_P13_START_DATE', '3_P6_MEDCODE'):
                    # skip and we'll do the drugs separately
                    continue
                else:
                    for i in range(1, field['repeat']+1):
                        lines.append(self._build_line(field['fields'], entry.apr_id,
                                site_mapping['site_id'], site_mapping['study_id'],
                                repeat=i))
        # Do the Drugs
        all_arvs = entry.arvtherapy_set.all()
        arvs = all_arvs
        cur_copy_id = 1
        while len(arvs) > 0:
            self._generate_drug_page(site_mapping, entry, lines, arvs[0:5], cur_copy_id)
            arvs = arvs[5:]
            cur_copy_id += 1

        return lines

    def _generate_drug_page(self, site_mapping, entry, lines, arvs, cur_copy_id=1):
        """
        Takes an array of up to 5 arv therapy entries at a time, and generates
        them on a page with the copy_id. This is to take care of the issue that 
        we can only have 5 entries on a single page at a time.
        """
        cur_drug = 1
        course_field = self.oc['3_P7_COURSE']
        startdate_field = self.oc['3_P13_START_DATE']
        medcode_field = self.oc['3_P6_MEDCODE']
        stopdate_field = self.oc['3_P14_STOP_DATE']
        ongoing_field = self.oc['3_P16_ONGOING']

        for field_name, field in self.oc.iteritems():
            if not field_name.startswith("3_"):
                continue
            if type(field) == list:
                value = self._field_value(field_name, entry)
                lines.append(self._build_line(field, entry.apr_id,
                            site_mapping['site_id'], site_mapping['study_id'],
                            value=value, copy_id=cur_copy_id))
            else:
                #TODO Values for repeating fields
                #arvs = entry.arvtherapy_set.all()
                if field_name in ('3_P7_COURSE', '3_P13_START_DATE', '3_P6_MEDCODE', '3_P16_ONGOING', '3_P14_STOP_DATE'):
                    # skip and we'll do the drugs separately
                    continue
                else:
                    for i in range(1, field['repeat']+1):
                        lines.append(self._build_line(field['fields'], entry.apr_id,
                                site_mapping['site_id'], site_mapping['study_id'],
                                repeat=i, copy_id=cur_copy_id))

        for arv in arvs:
            if cur_drug == 6:
                #TODO We need to use a different page format for more than 5 drugs
                break
            lines.append(self._build_line(course_field['fields'], entry.apr_id,
                site_mapping['site_id'], site_mapping['study_id'],
                repeat=cur_drug, value=arv.course, copy_id=cur_copy_id))
            lines.append(self._build_line(startdate_field['fields'], entry.apr_id,
                site_mapping['site_id'], site_mapping['study_id'],
                repeat=cur_drug, value=arv.date_began.strftime('%Y%m%d'), copy_id=cur_copy_id))
            lines.append(self._build_line(medcode_field['fields'], entry.apr_id,
                site_mapping['site_id'], site_mapping['study_id'],
                repeat=cur_drug, value=arv.medcode, copy_id=cur_copy_id))
            # Stop Date
            if arv.date_ended == None:
                stop_date_val = ''
            else:
                stop_date_val = arv.date_ended.strftime('%Y%m%d')
            lines.append(self._build_line(stopdate_field['fields'], entry.apr_id,
                site_mapping['site_id'], site_mapping['study_id'],
                repeat=cur_drug, value=stop_date_val, copy_id=cur_copy_id))
            # Ongoing
            ongoing_val = arv.ongoing 
            if ongoing_val != 1:
                ongoing_val = ''
            lines.append(self._build_line(ongoing_field['fields'], entry.apr_id,
                site_mapping['site_id'], site_mapping['study_id'],
                repeat=cur_drug, value=ongoing_val, copy_id=cur_copy_id))

            cur_drug += 1
        # while cur_drug < 6:
        #     lines.append(self._build_line(course_field['fields'], entry.apr_id,
        #         site_mapping['site_id'], site_mapping['study_id'],
        #         repeat=cur_drug, copy_id=cur_copy_id))
        #     lines.append(self._build_line(startdate_field['fields'], entry.apr_id,
        #         site_mapping['site_id'], site_mapping['study_id'],
        #         repeat=cur_drug, copy_id=cur_copy_id))
        #     lines.append(self._build_line(medcode_field['fields'], entry.apr_id,
        #         site_mapping['site_id'], site_mapping['study_id'],
        #         repeat=cur_drug, copy_id=cur_copy_id))
        #     cur_drug += 1

    def _field_value(self, field_name, entry):
        mapping = self.apr_map
        if not mapping.has_key(field_name):
            return ''
        elif mapping[field_name] == 'empty':
            return ''
        elif type(mapping[field_name]) == dict:
            if mapping[field_name]['type'] == 'literal':
                return mapping[field_name]['value']
        elif mapping[field_name] == "child.birthdate":
            return entry.child.birthdate.strftime('%Y%m%d')
        elif mapping[field_name] == "child.gender":
            return entry.child.gender
        elif mapping[field_name] == "baby_id":
            #TODO add support for twins
            return str(entry.apr_id)+"1"
        elif mapping[field_name] == "sponsor_formatted_patient_id":
            return "IEDEA-"+str(entry.apr_id)[1:]
        elif mapping[field_name].startswith('entry.'):
            value = getattr(entry, mapping[field_name][6:])
            if type(value) == datetime.date or type(value) == datetime.datetime:
                return value.strftime('%Y%m%d')
            elif value == None:
                return ''
            else:
                return value
        else:
            raise Exception("Unknown type: " + str(mapping[field_name]))

    def _build_line(self, fields, reg_id, site_id, study_id, value='', copy_id=1, repeat=1 ):
        return [
            'APR'+str(site_id),
            'APR'+str(site_id),
            reg_id,
            str(site_id)+str(reg_id)+str(fields[-1])+str(copy_id),
            fields[0],
            str(copy_id-1),
            self.timestamp,
            '',
            fields[1],
            fields[2],
            fields[3],
            fields[4],
            fields[5],
            0,
            repeat,
            value,
            '',
            str(fields[-1]).zfill(3),
            study_id
        ]

    def _serialize_lines(self, lines):
        """
        Takes a list of lines and converts them into the pipe delimited format required
        by the registry.
        """
        togo = []
        for line in lines:
            togo.append("|".join([str(l) for l in line]))
        return "\n".join(togo)
