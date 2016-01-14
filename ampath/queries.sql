-- Random sql queries for AMPATH data

select e.patient_id, e.encounter_datetime, e.form_id from obs o, encounter e where 
concept_id = 6245 and value_coded = 6242
and o.encounter_id = e.encounter_id 
and e.encounter_datetime >= "2014-01-01" and e.encounter_datetime < "2015-09-01"
and e.voided = 0
order by encounter_datetime;

select * from form where form_id in (97, 257, 378);

select * from encounter_type where encounter_type_id in (32, 3);