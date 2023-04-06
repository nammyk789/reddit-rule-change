import json
from pprint import pprint
from collections import OrderedDict, Counter
import csv
import datetime

file1_path = "original data/full_reddit_metadata_apr_23.jsonl"
file2_path = "original data/full_subreddit_metadata_dec_10.jsonl"
# file1_path = "test1.jsonl"
# file2_path = "test2.jsonl"

def standardizeRule(source:str, sub:dict, r:dict, scrape_line:int, date_observed:str):
    """ get a scraped rule into standard form"""
    subname = sub["sub_name"].lower()
    r_copy = {} # create a copy of the rule where key names are consistent
    r_copy['source'] = source
    r_copy['date_observed'] = date_observed #TODO: figure out what this is for
    r_copy['rule_count'] = len(sub['rules_widget'])
    r_copy['scrape_count'] = sub_counter[subname]
    r_copy['scrape_line'] = scrape_line
    r_copy['created_utc'] = r['createdUtc']
    r_copy['description'] = r['description']
    r_copy['priority'] = r['priority']
    r_copy['short_name'] = r['shortName']
    r_copy['violation_reason'] = r['violationReason']
    return OrderedDict( sorted(r_copy.items() ) )

count = 0  # these two values are for testing on subsets
max_count = 100000  # these two values are for testing on subsets
sub_count = 0
subs_1 = [] # subs from the first file
subs_2 = [] # subs from the second file
sub_rule_versions = {}
sub_rule_names = {}
sub_descriptions = {}
sub_timestamps = {}
sub_metadata = {}
sub_counter = Counter()
drop_subs = []
low_num_subscribers = []

existing_rule_count = 0
refurb_rule_count = 0
new_rule_count = 0
errors = 0
date_of_first_scrape = datetime.datetime(2021, 4, 23)
one_month_before_first_scrape = date_of_first_scrape - datetime.timedelta(days=30)
one_month_before_first_scrape = int(one_month_before_first_scrape.timestamp())



print("processing April 23rd scrape")
with open(file1_path) as apr_23:
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
        except: # if any of those fields are missing, drop the sub
            drop_subs.append(subname)
            continue

        if sub['created_utc'] <= one_month_before_first_scrape: # drop if sub is too young
            drop_subs.append(subname)
            continue
        else:
            subs_1.append(subname)
            sub_counter[subname] += 1

        ## build structure up
        if not subname in sub_rule_versions:
            ### bookkeeping
            sub_rule_versions[subname] = {}
            sub_rule_names[subname] = []
            sub_descriptions[subname] = []
            sub_timestamps[subname] = []
        for r in sub['rules_widget']:
            r = standardizeRule('apr_23', sub, r, i, "April 23")


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
        sub_count += 1
        # if count > max_count:
        #     break
        count += 1

count = 0
print("processing December 10th scrape")
with open(file2_path) as dec_10:
    for i, line in enumerate(dec_10):
        try:
            sub = json.loads(line)
        except:
            errors += 1
            continue
        subname = sub['sub_name'].lower()
        if sub_counter[subname] != 1 or subname in drop_subs:
            continue # we only want subs that are in both snapshots, and we want to skip duplicates
        
        # get metadata
        try:
            sub_metadata[subname]['subscribers_2'] = int(sub['subscribers'])
            sub_metadata[subname]['rules_2'] = len(sub['rules_widget'])
            subs_2.append(subname)
            sub_counter[subname] += 1
        except:
            drop_subs.append(subname)
            continue

        # drop subs that have too few subscribers
        if sub_metadata[subname]['subscribers_1'] < 3 and sub_metadata[subname]['subscribers_2'] < 3:
            drop_subs.append(subname)
            continue
        # drop subs that have no rules in both scrapes
        elif sub_metadata[subname]['rules_1'] < 1 and sub_metadata[subname]['rules_2'] < 1:
            drop_subs.append(subname)
            continue

        if subname not in sub_rule_versions:
            ### bookkeeping
            sub_rule_versions[subname] = {}
            sub_rule_names[subname] = []
            sub_descriptions[subname] = []
            sub_timestamps[subname] = []
            sub_count += 1
        for r in sub['rules_widget']:
            r = standardizeRule('dec_10', sub, r, i, 'December 10')
        
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
                        drop_subs.append(subname)
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
        sub_count += 1
        # if count > max_count:
        #     break
        count += 1
print('Finished processing scrapes')

# remove subs that are not in both snapshots and subs that weren't processed properly
intersection = list(set(subs_1) & set(subs_2)) # subs that are in both snapshots
not_in_both = [sub for sub in set(subs_1) if sub not in set(subs_2)]
not_in_both.extend([sub for sub in set(subs_2) if sub not in set(subs_1)])
drop_subs.extend(not_in_both)

for sub in set(drop_subs):
    if sub in sub_rule_versions:
        sub_rule_versions.pop(sub)

subs_scraped = set(sub_rule_versions.keys())
for sub in subs_scraped:
    if sub_counter[sub] != 2 or sub in drop_subs:
        sub_rule_versions.pop(sub)


with open('seth snapshot processing pipeline/step0_rules_merged_test.json', 'w') as outfile:
    json.dump(sub_rule_versions, outfile)
print( 'SCRIPT end' )

header = ('communityID', 'subscribers_1', 'subscribers_2', 'rules_1', 'rules_2', 'founding_date')
with open('seth snapshot processing pipeline/metadata.csv', 'w', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=header)
    writer.writeheader()
    for sub in sub_metadata:
        if sub_counter[sub] == 2 and sub not in drop_subs:
            sub_data = sub_metadata[sub]
            data_out = {
                            'communityID' : sub
                            , 'subscribers_1' : sub_data['subscribers_1']
                            , 'subscribers_2' : sub_data['subscribers_2']
                            , 'rules_1' : sub_data['rules_1']
                            , 'rules_2' : sub_data['rules_2']
                            , 'founding_date' : sub_data['founding_date']
                        }
            writer.writerow(data_out)


print(f"errors: {errors}")
