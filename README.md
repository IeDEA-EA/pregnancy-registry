IeDEA Pregnancy Registry
========================

Collection of scripts and documentation for the pregnancy-registry

These utilities generate the cohorts for both AMPATH and FACES Encounters mapped
to their respectice concept dictionaries, and then serialize those cohorts to
the import format expected by INC Research who runs an OC Database to store the
results.

## Overview

## Installation

## Configuration

Two database connections are required to run this utility.  One of them is for
the local storage of exported pregnancy items.  Initially this database will 
need to be synced to create the tables.

The second database connection will be to the OpenMRS MySQL instance to pull 
data from.  This can be a production DB, or preferably a clone of production 
used for reporting tasks.  This connection can be read only (preferably).

These connections are specified in `pregreg/secure.py`. This contains database
credentials and should only be readable by the user running the reports. 
Alternatively, this file is a regular python source, so if you prefer to read 
credentials from an environment variable, keyring, or that store that can also
be done.

```python
DATABASES = {
    'apr_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'apr_db',
        'USER': 'apruser',
        'PASSWORD': '********',
        'HOST': 'localhost',   # Or an IP Address that your DB is hosted on
        'PORT': '3306',
    },
    'amrs_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'amrs',
        'USER': 'amrs_user',
        'PASSWORD': '********',
        'HOST': 'openmrs.ampath.org',
        'PORT': '3306',
    },
    'faces_openmrs_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'openmrs',
        'USER': 'faces_user',
        'PASSWORD': '********',
        'HOST': 'openmrs.faces.org',
        'PORT': '3306',
    },
}
```

## Usage

To run the cohort for a given set of months use the below syntax. The following
will generate the cohort entries for January, February, and March 2014.

```
generate_cohort 2014 1,2,3
```

To export the results in OC format after they have been generated, the following
command is used. This will generate the report for February 2014 and write it 
to a file in your working directory called `export-file.txt`.

```
generate_report 2014 2 export-file.txt
```
