import json

#class EmrRouter(object):
#    """
#    A router to control all database operations on models in the
#    auth application.
#    """
#    def db_for_read(self, model, **hints):
#        """
#        Attempts to read auth models go to auth_db.
#        """
#        if model._meta.app_label == 'emr':
#            return 'emr_db'
#        return None
#
#    def db_for_write(self, model, **hints):
#        """
#        Attempts to write emr models go to emr_db.
#        """
#        if model._meta.app_label == 'emr':
#            return 'emr_db'
#        return None
#
#    def allow_relation(self, obj1, obj2, **hints):
#        """
#        Allow relations if a model in the emr app is involved.
#        """
#        if obj1._meta.app_label == 'emr' or \
#           obj2._meta.app_label == 'emr':
#           return True
#        return None
#
#    def allow_migrate(self, db, model):
#        """
#        Make sure the emr app only appears in the 'emr_db'
#        database.
#        """
#        if db == 'emr_db':
#            return model._meta.app_label == 'emr'
#        elif model._meta.app_label == 'auth':
#            return False
#        return None
#

def dump_arv_codes(mapping_name='faces-mapping'):
    print "Using mapping: ", mapping_name
    schemafile = './apr/registry-schema.json'
    with open(schemafile) as f:
        schema = json.loads(f.read())
    arvs = schema[mapping_name]['arvs']
    for concept_id, arv in arvs.iteritems():
        print arv['medcode'], arv['desc']
