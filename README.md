IeDEA Pregnancy Registry
========================

Collection of scripts and documentation for the pregnancy-registry

These utilities generate the cohorts for both AMPATH and FACES Encounters mapped
to their respectice concept dictionaries, and then serialize those cohorts to
the import format expected by INC Research who runs an OC Database to store the
results.

## Installation

## Configuration

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
