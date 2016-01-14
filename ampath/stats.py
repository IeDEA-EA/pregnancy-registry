from django.db import connections
cursor = connections['default'].cursor()

# Lot's of SQL in this file that doesn't use proper injection scrubbing. This is 
# a utility and shouldn't be served to a user editable webpage.

def stats_for_range(start=(2014,1), end=(2014,2)):
    start_date = "%s-%s-01" % (start[0], start[1])
    end_date = "%s-%s-01" % (end[0], end[1])

    print "\nStats for: %s  to %s" % (start_date, end_date,)
    cursor.execute(
        """select distinct(voided), count(voided) from apr_ampath_db.apr_registryentry 
    where cohort_date >= '%s' and cohort_date < '%s'
    group by voided
    order by voided""" % (start_date, end_date))
    res = cursor.fetchall()
    print "Cohort Size: ", res[0][1]
    print "Voided: ", res[1][1]

    cursor.execute(
        """select distinct(voided_reason), count(voided_reason) from apr_ampath_db.apr_registryentry 
        where cohort_date >= '%s' and cohort_date < '%s' and voided = True
        group by voided_reason
        order by voided_reason""" % (start_date, end_date))
    res = cursor.fetchall()
    for i in res:
        print "Voided Reason/Count ", i[0], i[1]

    #print ""
    # cursor.execute(
    #     """select count(voided_duplicate) from apr_ampath_db.apr_registryentry 
    # where cohort_date >= '%s' and cohort_date < '%s' and voided = True""" % (start_date, end_date))
    # print cursor.fetchall()[0][0]
    # 
    # cursor.execute(
    #     """select count(voided_too_old_at_paeds_encounter) from apr_ampath_db.apr_registryentry 
    # where cohort_date >= '%s' and cohort_date < '%s' and voided = True""" % (start_date, end_date))
    # print cursor.fetchall()[0][0]
    # 
    # cursor.execute(
    #     """select count(voided_mother_not_linked) from apr_ampath_db.apr_registryentry 
    # where cohort_date >= '%s' and cohort_date < '%s' and voided = True""" % (start_date, end_date))
    # print cursor.fetchall()[0][0]
    # 
    # cursor.execute(
    #     """select count(voided_no_arv_history) from apr_ampath_db.apr_registryentry 
    # where cohort_date >= '%s' and cohort_date < '%s' and voided = True""" % (start_date, end_date))
    # print cursor.fetchall()[0][0]
    # 
    # cursor.execute(
    #     """select count(voided_duplicate) from apr_ampath_db.apr_registryentry 
    # where cohort_date >= '%s' and cohort_date < '%s' and voided = True""" % (start_date, end_date))
    # print cursor.fetchall()[0][0]

def stats_for_all_months():
    stats_for_range(start=(2014,1), end=(2014,2))
    stats_for_range(start=(2014,2), end=(2014,3))
    stats_for_range(start=(2014,3), end=(2014,4))
    stats_for_range(start=(2014,4), end=(2014,5))
    stats_for_range(start=(2014,5), end=(2014,6))
    stats_for_range(start=(2014,6), end=(2014,7))
    stats_for_range(start=(2014,7), end=(2014,8))
    stats_for_range(start=(2014,8), end=(2014,9))
    stats_for_range(start=(2014,9), end=(2014,10))
    stats_for_range(start=(2014,10), end=(2014,11))
    stats_for_range(start=(2014,11), end=(2014,12))
    stats_for_range(start=(2014,12), end=(2015,1))

    stats_for_range(start=(2015,1), end=(2015,2))
    stats_for_range(start=(2015,2), end=(2015,3))
    stats_for_range(start=(2015,3), end=(2015,4))
    stats_for_range(start=(2015,4), end=(2015,5))
    stats_for_range(start=(2015,5), end=(2015,6))
    stats_for_range(start=(2015,6), end=(2015,7))
    