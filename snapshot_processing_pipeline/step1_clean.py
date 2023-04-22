#!/usr/bin/env python 
#filetype=python
"""
go through rules and make sure data fit strict assumptions. also enrich it with useful metadata
"""
import json
from pprint import pprint
from datetime import datetime
import numpy as np
from numpy import diff, argsort

def run_step1(data_directory:str):
    drop_subs = []
    DO_LEVENSHTEIN = True
    ### helpers
    #from: https://stackabuse.com/levenshtein-distance-and-text-similarity-in-python/
    # The distance value describes the minimal number of deletions, insertions, or substitutions 
    # that are required to transform one string (the source) into another (the target). 
    def levenshtein(seq1, seq2):
        if seq1 == seq2:
            return 0
        if seq1 == None:
            seq1 = ""
        if seq2 == None:
            seq2 = ""
        size_x = len(seq1) + 1
        size_y = len(seq2) + 1
        matrix = np.zeros ((size_x, size_y))
        for x in range(size_x):
            matrix [x, 0] = x
        for y in range(size_y):
            matrix [0, y] = y

        for x in range(1, size_x):
            for y in range(1, size_y):
                if seq1[x-1] == seq2[y-1]:
                    matrix [x,y] = min(
                        matrix[x-1, y] + 1,
                        matrix[x-1, y-1],
                        matrix[x, y-1] + 1
                    )
                else:
                    matrix [x,y] = min(
                        matrix[x-1,y] + 1,
                        matrix[x-1,y-1] + 1,
                        matrix[x,y-1] + 1
                    )
        #print (matrix)
        return( int( matrix[size_x - 1, size_y - 1]) )

    rule_meta_data = {}
    allrules  = {}
    with open(f'{data_directory}/step0_rules_merged.json', 'r') as rules_file:
        allrules = json.load( rules_file )
        print( "num subs total:", len( allrules ) )
        sub_count = 0
        for subname, rules in allrules.items():
            #print( subname )
            # bookkeeping
            sub_count += 1
            rule_meta_data[subname] = {}

            ### BUILD
            ### first get timestamps of all vrsions
            rule_edit_times = [] #edit times of all versions of all rules
            rule_edit_min_times = [] # minimum edit time of all versions of all rules
            scrape_times = {} # get average creation time of all versions from a given scrape
            for rname, rule_versions in rules.items():
                version_edit_times = [] # edit times of all versions of all rules
                version_observed_times = [] # date observed of all versions of all rules
                # BUILD
                for version in rule_versions:
                    version['created_utc'] = int( version['created_utc'] )
                    version['created_utc_date'] = datetime.fromtimestamp(version['created_utc']).strftime('%Y-%m')
                    rule_edit_times.append( version['created_utc'] )
                    version_edit_times.append( version['created_utc'] )
                    version_observed_times.append( version['date_observed'] )
                    if version['scrape_count'] not in scrape_times:
                        scrape_times[ version['scrape_count'] ] = []
                    scrape_times[ version['scrape_count'] ].append( version['created_utc'] )
                ### TEST
                ### versions must be in the right order. whatever that means.  but some reddit scapres are from before the wayback scrape. weird.
                ### get "raw" edit times before cleaning edit times in versions
                if version_edit_times != sorted(version_edit_times): 
                    rule_versions.reverse()
                    version_edit_times.reverse()
                    assert( len(version_edit_times) == 2 ) # else I need a more complicated fix that reverse and more diagnoisois
                assert( version_edit_times == sorted(version_edit_times) )
                if len(version_edit_times) == 2 :
                    if datetime.strptime(rule_versions[0]['date_observed'], '%Y-%m-%d %H:%M:%S') > datetime.strptime(rule_versions[1]['date_observed'], '%Y-%m-%d %H:%M:%S'):  
                        ### this is a wired thing that shouldn't happen but does
                        # pprint( rule_versions )
                        drop_subs.append(subname)
                # BUILD
                # record the earliest version of this rule
                rule_edit_min_times.append( min( version_edit_times))

            ### BUILD
            ### rules are sorted by average of version edit times
            ### SORT OF: they're stored in dict, which doesn't have order ugh
            for i, rule_versions in enumerate(rules.values()):
                for version in rule_versions:
                    ### convert to list of ints from ndarray of int64s (for json dump)
                    ### TODO refactor this into having python native output
                    version['rule_order_master'] =  rule_edit_min_times[ int(argsort( rule_edit_min_times).tolist()[i]) ]
            assert( len(rule_edit_min_times) == len( rules ) )
            assert( len(rule_edit_times) >= len( rules ) )

            ### TRACK
            ### get a representation of the order of the rules
            ### get a representation of the al rule creation times
            ### get the "effective creation date" of the sub's rules, the date up to a month after the earliest rule creation date
            rule_meta_data[subname]['rule_count'] = len( rules )
            rule_meta_data[subname]['rule_creation_times'] = rule_edit_min_times
            rule_meta_data[subname]['rule_creation_times_full'] = rule_edit_times
            rule_meta_data[subname]['rule_observed_times'] = version_observed_times
            ### convert to list of ints from ndarray of int64s (for json dump)
            rule_meta_data[subname]['rule_order'] = [int(i) for i in argsort( rule_edit_min_times)]
            first_sub_rule_creation = min( rule_edit_times )
            rule_meta_data[subname]['sub_first_rule_creation_time'] = first_sub_rule_creation
            assert( min( rule_meta_data[subname]['rule_order'] ) == 0 )
            assert( max( rule_meta_data[subname]['rule_order'] ) == len( rule_meta_data[subname]['rule_order'] ) - 1 )

            ### TEST
            ### confirm that rule with master order 1 has time equal to first_sub_rule_creation
            for i, (rname, rule_versions) in enumerate(rules.items()):
                version_edit_times = [ v['created_utc'] for v in rule_versions]
                if rule_versions[0]['rule_order_master'] == 0:
                    try:
                        assert( min(version_edit_times) == first_sub_rule_creation )
                    except:
                        print()
                        print( subname, rname)
                        print(  min(version_edit_times), first_sub_rule_creation, min(version_edit_times) == first_sub_rule_creation, version_edit_times )
                        pprint( rule_meta_data[subname])
                        print([int(i) for i in argsort( rule_edit_min_times)])
                        print([i for i in argsort( rule_edit_min_times)])
                        print( rule_edit_min_times)
                        pprint( rule_versions)
                        raise

            ### BUILD
            # create rule_presence boolean list. len num of versions + 1.  was rule present at founding?
            rules_at_founding = []
            for i, versions in enumerate(rules.values()):
                to_add = False
                # to be registeresd as present during creation, a rule needs to have a wayback scrape and needs to have been present within a month of the first rule seen
                # UGH!  or not.  there exist rules that were present at creation, that are only in reddit.
                if True or any([ v['source'] == 'earliest' for v in versions ]):
                    for v in versions:
                        if v['created_utc'] - first_sub_rule_creation < 60*60*24*7*4:
                            to_add = True
                rules_at_founding.append( to_add )
            rule_meta_data[subname]['rules_present_at_creation'] = rules_at_founding

            ### TEST
            ### if any rules were added, it's the last ones that were created
            ###   if any rules were labeled as added, they were the last in the list of rules
            num_original = sum( [ 1 for i in rules_at_founding if i ] )
            num_added = sum( [ 1 for i in rules_at_founding if not i ] )
            rule_order = rule_meta_data[subname]['rule_order']
            for index, presence in enumerate( [rules_at_founding[i] for i in rule_order] ):
                if index < (len(rules_at_founding) - num_added):
                    assert( presence )
                else:
                    assert( not presence )


            ### TEST
            ### : if no rules were labeled as added, the creation batch date span for the last rules is the same as for the first
            ### : if no rules were labeled as added, the creation batch date span is less thana  month for all pairs of rules (orall against the first)
            if num_added == 0:
                assert( abs( rule_edit_min_times[min(rule_order)] - rule_edit_min_times[max(rule_order)] ) < 60*60*24*7*4 )
                assert( all([abs( rule_edit_min_times[0] - r) < 60*60*24*7*4  for r in  rule_edit_min_times]) )

            ### BUILD
            # create rule_presence boolean list. len num of versions + 1.  was rule present in each scrape?
            rules_at_earliest_scrape = []
            rules_at_latest_scrape = []
            for i, versions in enumerate(rules.values()):
                versions_at_earliest_scrape = [v['source'] == 'earliest' for v in versions]
                versions_at_latest_scrape = [v['source'] == 'latest' for v in versions]
                rules_at_earliest_scrape.append( any( versions_at_earliest_scrape ) )
                rules_at_latest_scrape.append( any( versions_at_latest_scrape ) )
                if any(versions_at_earliest_scrape):
                    assert( any([v['source'] == 'earliest' for v in versions]))
                if any(versions_at_latest_scrape):
                    assert( any([v['source'] == 'latest' for v in versions]))
            assert([ r1 ^ r2 for r1, r2 in zip(rules_at_earliest_scrape, rules_at_latest_scrape)])
            rule_meta_data[subname]['rules_present_in_earliest_scrape'] = rules_at_earliest_scrape
            if rules_at_earliest_scrape[0] != rule_meta_data[subname]['rules_present_at_creation'][0]:
                drop_subs.append(subname)
            rule_meta_data[subname]['rules_present_in_latest_scrape'] = rules_at_latest_scrape

            ### BUILD
            # measure distance of neighboring versions from each other
            description_differences = []
            description_distances = []
            short_name_distances = []
            violation_reason_distances = []
            rule_num = 0
            for versions in rules.values():
                ruleID = f"{subname}_{rule_num}"
                if len(versions) == 2:
                    description_difference = 0 if versions[0]['description'] == versions[1]['description'] else 1
                    if DO_LEVENSHTEIN :
                        description_distance = levenshtein( versions[0]['description'], versions[1]['description'] )
                        short_name_distance = levenshtein( versions[0]['short_name'], versions[1]['short_name'] )
                        violation_reason_distance = levenshtein( versions[0]['violation_reason'], versions[1]['violation_reason'] )

                    else:
                        description_distance = 0 if versions[0]['description'] == versions[1]['description'] else 10
                        short_name_distance = 0 if versions[0]['short_name'] == versions[1]['short_name'] else 10
                        violation_reason_distance = 0 if versions[0]['violation_reason'] == versions[1]['violation_reason'] else 10
                elif len(versions) == 1:
                    description_distance = float("Inf")
                    description_difference = float("Inf")
                    short_name_distance = float("Inf")
                    violation_reason_distance = float("Inf")
                else:
                    print(f'{subname} had a rule with more than two versions')
                    drop_subs.append(subname)
                description_distances.append( description_distance )
                short_name_distances.append( short_name_distance )
                violation_reason_distances.append( violation_reason_distance )
                for v in versions:
                    v['rule_ID'] = ruleID
                description_differences.append( description_difference )
                rule_num += 1
            rule_meta_data[subname]['rules_description_difference'] = description_differences
            rule_meta_data[subname]['rules_description_distance'] = description_distances
            rule_meta_data[subname]['rules_short_name_distance'] = short_name_distances
            rule_meta_data[subname]['rules_violation_reason_distance'] = violation_reason_distances


        # get rid of violations
        for sub in set(drop_subs):
            allrules.pop(sub)
            rule_meta_data.pop(sub)

        print( "num subs total:", len(allrules) )
        print( "violations:", len(set(drop_subs)))

        if DO_LEVENSHTEIN:
            filename = f'{data_directory}/step1_rules_cleaned.json'
        else:
            filename = f'{data_directory}/step1_rules_cleaned_fast.json'
        with open(filename, 'w') as outfile1:
            print( len( allrules ) )
            json.dump(allrules, outfile1)
        with open(f'{data_directory}/step1_rules_metadata.json', 'w') as outfile2:
            print( len( rule_meta_data ) )
            json.dump(rule_meta_data, outfile2)

if __name__ == '__main__':
    data_directory = 'c:/Users/nammy/Desktop/reddit-rule-change/output_data/seth'
    run_step1(data_directory)
