import json
from pprint import pprint
from collections import OrderedDict, Counter
import csv
import datetime

sub_counter = Counter()

def standardizeRule(source:str, sub:dict, r:dict, scrape_line:int, date_observed:str):
    """ get a scraped rule into standard form"""
    subname = sub["sub_name"].lower()
    r_copy = {} # create a copy of the rule where key names are consistent
    r_copy['source'] = source
    r_copy['date_observed'] = date_observed 
    r_copy['rule_count'] = len(sub['rules_widget'])
    r_copy['scrape_count'] = sub_counter[subname]
    r_copy['scrape_line'] = scrape_line
    r_copy['created_utc'] = r['createdUtc']
    r_copy['description'] = r['description']
    r_copy['priority'] = r['priority']
    r_copy['short_name'] = r['shortName']
    r_copy['violation_reason'] = r['violationReason']
    return OrderedDict( sorted(r_copy.items() ) )


def run_step0_seth(scrape1_path: str, scrape2_path:str, output_directory:str):
    count = 0  # these two values are for testing on subsets
    max_count = 10000  # these two values are for testing on subsets
    subs_1 = [] # subs from the first file
    sub_rule_versions = {}
    sub_rule_names = {}
    sub_descriptions = {}
    sub_timestamps = {}
    sub_metadata = {}
    global sub_counter
    drop_subs = Counter()

    existing_rule_count = 0
    refurb_rule_count = 0
    new_rule_count = 0
    errors = 0
    date_of_first_scrape = datetime.datetime(2021, 4, 23)
    one_month_before_first_scrape = date_of_first_scrape - datetime.timedelta(days=30)
    one_month_before_first_scrape = int(one_month_before_first_scrape.timestamp())
    too_young = 0
    first_scrape_sub_counter = Counter()

    print("processing first scrape")
    with open(scrape1_path) as apr_23:
        for i, line in enumerate(apr_23):
            try:
                sub = json.loads(line)
            except:
                errors += 1
                continue
            subname = sub['sub_name'].lower()

            if sub_counter[subname] > 0: # skip duplicates
                continue

            # get metadata
            sub_metadata[subname] = {}
            try:
                sub_metadata[subname]['subscribers_1'] = int(sub['subscribers'])
                sub_metadata[subname]['rules_1'] = len(sub['rules_widget'])
                sub_metadata[subname]['founding_date'] = sub['created_utc']
                sub_metadata[subname]['timestamp_1'] = sub['timestamp']
                first_scrape_sub_counter[subname] += 1
            except: # if any of those fields are missing, drop the sub
                drop_subs[subname] += 1
                continue

            if sub['created_utc'] >= one_month_before_first_scrape: # drop if sub is too young
                drop_subs[subname] += 1
                too_young += 1
                continue
            else:
                sub_counter[subname] += 1

            ## build structure up
            if not subname in sub_rule_versions:
                ### bookkeeping
                sub_rule_versions[subname] = {}
                sub_rule_names[subname] = []
                sub_descriptions[subname] = []
                sub_timestamps[subname] = []
            for r in sub['rules_widget']:
                r = standardizeRule('earliest', sub, r, i, '2021-04-23 00:00:00')


                ### aggregate
                ## decide whether to add rule version to list of alternative rule versions
                # Rules can differ in strange ways. 
                # *  They can be identical except for the 'kind' or 'priority' keys. 
                # *  The rule name can change to reflect on a priority change and not content change
                # *  the description can change completely but created_utc timestamp stays the same (so created_utc is no test of ddifference)
                # NOPE: so if description is accounted for, I won't add rule to copies, even if there was an interesting chnge in the short_name
                # rule creation times persist after edits, and are precise to the second, so two different rules 
                #  (in terms of short name) withthe same creation date are cases fo the shortname changingeven though thr rule is the same
                # clean shortname for suitability as key
                effective_rname = ''
                if r['short_name'] in sub_rule_names[subname]:
                    effective_rname = r['short_name']
                    sub_timestamps[subname].append( r['created_utc'] )
                    existing_rule_count += 1

                else:
                    flow_through = True
                    ### this is a way too complicated step to solve a funny problem that rule versions don't have unique ID's between scrapes, 
                    # and the "same rule" can differ on name, description, order, creation_date, etc, while different rules can have the same of any of those.
                    if r['created_utc'] in sub_timestamps[subname] and r['description'] in sub_descriptions[subname]:
                        ## this rule is a candidate for a preexisting rule with a different short name
                        candidate_rule_name = sub_rule_names[subname][ sub_timestamps[subname].index(r['created_utc']) ]
                        candidate_rule = sub_rule_versions[subname][candidate_rule_name]
                        cand_datalines = [ v['scrape_line'] for v in candidate_rule] # which lines in file do they come from
                        cand_descs = [ v['description'] for v in candidate_rule]
                        cand_violations = [ v['violation_reason'] for v in candidate_rule]
                        cand_names = [ v['short_name'] for v in candidate_rule]
                        if r['scrape_line'] not in cand_datalines: 
                            if (
                                ( r['description'] and r['description'] in cand_descs) or
                                ( r['violation_reason'] and r['violation_reason'] in cand_violations ) or
                                ( r['short_name'] and r['short_name'] in cand_names)
                            ):
                                ### add rule version to the short_name entry that has the same already existing rule creation date
                                effective_rname = candidate_rule_name
                                refurb_rule_count += 1
                                flow_through = False
                    elif r['created_utc'] in sub_timestamps[subname] and r['description'] not in sub_descriptions[subname]:
                        # this chunk never runs
                        break
                    if flow_through:
                        effective_rname = r['short_name']
                        sub_rule_versions[subname][ r['short_name'] ] = []
                        sub_rule_names[subname].append( r['short_name'] )
                        sub_timestamps[subname].append( r['created_utc'] )
                        new_rule_count += 1
                    sub_descriptions[subname].append( r['description'] )
                sub_rule_versions[subname][ effective_rname ].append( r )
            # if count > max_count:
            #     break
            # count += 1

    count = 0
    too_few_subs = 0
    zero_rules = 0
    second_scrape_sub_counter = Counter()
    print("processing second scrape")
    with open(scrape2_path) as dec_10:
        for i, line in enumerate(dec_10):
            try:
                sub = json.loads(line)
            except:
                errors += 1
                continue
            subname = sub['sub_name'].lower()

            if sub_counter[subname] != 1:
                second_scrape_sub_counter[subname] +=1
                continue # we only want subs that are in both snapshots, and we want to skip duplicates

            elif drop_subs[subname] > 0:
                continue

            # get metadata
            try:
                sub_metadata[subname]['subscribers_2'] = int(sub['subscribers'])
                sub_metadata[subname]['rules_2'] = len(sub['rules_widget'])
                sub_metadata[subname]['timestamp_2'] = sub['timestamp']
                second_scrape_sub_counter[subname] += 1
            except:
                drop_subs[subname] += 1
                continue

            # drop subs that have too few subscribers
            if sub_metadata[subname]['subscribers_1'] < 3 and sub_metadata[subname]['subscribers_2'] < 3:
                drop_subs[subname] += 1
                too_few_subs += 1
                continue
            # drop subs that have no rules in both scrapes
            elif sub_metadata[subname]['rules_1'] < 1 and sub_metadata[subname]['rules_2'] < 1:
                drop_subs[subname] += 1
                zero_rules += 1
                continue
            
            else:
                sub_counter[subname] += 1

            if subname not in sub_rule_versions:
                ### bookkeeping
                sub_rule_versions[subname] = {}
                sub_rule_names[subname] = []
                sub_descriptions[subname] = []
                sub_timestamps[subname] = []
            for r in sub['rules_widget']:
                r = standardizeRule('latest', sub, r, i, '2021-12-10 00:00:00')
            
            ### aggregate
                ## decide whether to add rule version to list of alternative rule versions
                # Rules can differ in strange ways. 
                # *  They can be identical except for the 'kind' or 'priority' keys. 
                # *  The rule name can change to reflect on a priority change and not content change
                # *  the description can change completely but created_utc timestamp stays the same (so created_utc is no test of ddifference)
                # NOPE: so if description is accounted for, I won't add rule to copies, even if there was an interesting chnge in the short_name
                # rule creation times persist after edits, and are precise to the second, so two different rules 
                #  (in terms of short name) withthe same creation date are cases fo the shortname changingeven though thr rule is the same
                # clean shortname for suitability as key
                effective_rname = ''
                if r['short_name'] in sub_rule_names[subname]:
                    effective_rname = r['short_name']
                    sub_timestamps[subname].append( r['created_utc'] )
                    existing_rule_count += 1 

                else:
                    flow_through = True
                    ### this is a way too complicated step to solve a funny problem that rule versions don't have unique ID's between scrapes, 
                    # and the "same rule" can differ on name, description, order, creation_date, etc, while different rules can have the same of any of those.
                    if r['created_utc'] in sub_timestamps[subname] and r['description'] in sub_descriptions[subname]:
                        ## this rule is a candidate for a preexisting rule with a different short name
                        """ ran into a weird situation where a sub had multiple rules that only changed shortnames
                        between snaps, but many rules have the exact same creation time, so this indexing method
                        didn't work. because it was only one sub, I'm just skipping it"""
                        try:
                            candidate_rule_name = sub_rule_names[subname][ sub_timestamps[subname].index(r['created_utc']) ]
                        except:
                            drop_subs[subname] += 1
                            continue
                        candidate_rule = sub_rule_versions[subname][candidate_rule_name]
                        cand_datalines = [ v['scrape_line'] for v in candidate_rule] # which lines in file do they come from
                        cand_descs = [ v['description'] for v in candidate_rule]
                        cand_violations = [ v['violation_reason'] for v in candidate_rule]
                        cand_names = [ v['short_name'] for v in candidate_rule]
                        if r['scrape_line'] not in cand_datalines: 
                            if (
                                ( r['description'] and r['description'] in cand_descs) or
                                ( r['violation_reason'] and r['violation_reason'] in cand_violations ) or
                                ( r['short_name'] and r['short_name'] in cand_names)
                            ):
                                ### add rule version to the short_name entry that has the same already existing rule creation date
                                effective_rname = candidate_rule_name
                                refurb_rule_count += 1
                                flow_through = False
                    if flow_through:
                        effective_rname = r['short_name']
                        sub_rule_versions[subname][ effective_rname ] = []
                        sub_rule_names[subname].append( effective_rname )
                        sub_timestamps[subname].append( effective_rname )
                        new_rule_count += 1
                    sub_descriptions[subname].append( r['description'] )
                sub_rule_versions[subname][ effective_rname ].append( r )
            # if count > int(max_count/2):
            #     break
            # count += 1

    print('Finished processing scrapes')
    total_subs = list(first_scrape_sub_counter.keys()) + list(second_scrape_sub_counter.keys())
    subs_in_both = set(list(first_scrape_sub_counter.keys())).intersection(list(second_scrape_sub_counter.keys()))
    print(f'total subs in both scrapes: {len(set(total_subs))}')
    print(f"subs in first scrape: {len(first_scrape_sub_counter.keys())}")
    print(f"subs in second scrape: {len(second_scrape_sub_counter.keys())}")
    print(f"subs in both: {len(subs_in_both)}")
    print(f"subs that had zero rules in both scrapes: {zero_rules}")
    print(f"subs that had less than three subscribers in both scrapes: {too_few_subs}")
    print(f"subs that were less than a month old in the first scrape: {too_young}")

    # remove subs that are not in both snapshots and subs that weren't processed properly
    subs_scraped = set(sub_rule_versions.keys())
    for sub in subs_scraped:
        if sub_counter[sub] != 2 or drop_subs[sub] > 0:
            sub_rule_versions.pop(sub)

    print(f"remaining subs: {len(sub_rule_versions.keys())}")

    with open(f'{output_directory}/step0_rules_merged.json', 'w') as outfile:
        json.dump(sub_rule_versions, outfile)
    
    print( 'SCRIPT end' )

    header = ('communityID', 'subscribers_1', 'subscribers_2', 'rules_1', 'rules_2', 
              'timestamp_1', 'timestamp_2', 'founding_date')
    with open(f'{output_directory}/sub_metadata_step_0.csv', 'w', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=header)
        writer.writeheader()
        for sub in sub_metadata:
            if sub_counter[sub] == 2 and drop_subs[sub] == 0:
                sub_data = sub_metadata[sub]
                data_out = {
                                'communityID' : sub
                                , 'subscribers_1' : sub_data['subscribers_1']
                                , 'subscribers_2' : sub_data['subscribers_2']
                                , 'rules_1' : sub_data['rules_1']
                                , 'rules_2' : sub_data['rules_2']
                                , 'timestamp_1' : sub_data['timestamp_1']
                                , 'timestamp_2' : sub_data['timestamp_2']
                                , 'founding_date' : sub_data['founding_date']
                            }
                writer.writerow(data_out)


    print(f"errors: {errors}")


if __name__ == '__main__':
    scrape_1_path = 'c:/Users/nammy/Desktop/reddit-rule-change/original_data/full_reddit_metadata_apr_23.jsonl'
    scrape_2_path = 'c:/Users/nammy/Desktop/reddit-rule-change/original_data/full_subreddit_metadata_dec_10.jsonl'
    data_directory = 'c:/Users/nammy/Desktop/reddit-rule-change/output_data/seth'
    run_step0_seth(scrape_1_path, scrape_2_path, data_directory)
