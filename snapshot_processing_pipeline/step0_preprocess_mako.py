import json
import lzma
from pprint import pprint
from collections import OrderedDict, Counter
from datetime import datetime
import csv

max_count = 1 * 10**5  # for testing on subsets
sub_count = 0
sub_rule_versions = {}
sub_rule_names = {}
sub_descriptions = {}
sub_timestamps = {}
sub_timestamps_latest = {}
sub_metadata = {}
sub_counter = Counter()
earliest_drop_subs = {}
latest_drop_subs = {}

existing_rule_count = 0
refurb_rule_count = 0
new_rule_count = 0
errors = 0

def standardizeRule(source:str, sub:dict, r:dict, date_observed:str):
    """ get a scraped rule into standard form"""
    subname = sub['subreddit'].lower()
    r_copy = {} # create a copy of the rule where key names are consistent
    r_copy['source'] = source
    r_copy['date_observed'] = date_observed
    r_copy['rule_count'] = sub['rules_earliest']['rules']
    r_copy['scrape_count'] = sub_counter[subname]
    r_copy['created_utc'] = r['created_utc']
    r_copy['description'] = r['description']
    r_copy['priority'] = r['priority']
    r_copy['short_name'] = r['short_name']
    r_copy['violation_reason'] = r['violation_reason']
    return OrderedDict( sorted(r_copy.items() ) )


def getRuleName(r:dict, subname:str, latest_snap:bool=False):
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
    global sub_rule_names
    global sub_timestamps
    global sub_timestamps_latest
    global sub_rule_versions
    global sub_descriptions
    global existing_rule_count
    global refurb_rule_count
    global new_rule_count
    effective_rname = ''
    if r['short_name'] in sub_rule_names[subname]: # this only happens for rules in the latest snapshot
        effective_rname = r['short_name']
        # sub_timestamps[subname].append( r['created_utc'] ) # getting multiple instances of same timestamp
        # sub_rule_names[subname].append(r['short_name']) # same short name linked to multiple timestamps TODO: double check this
        existing_rule_count += 1



    else:
        flow_through = True
        ### this is a way too complicated step to solve a funny problem that rule versions don't have unique ID's between scrapes, 
        # and the "same rule" can differ on name, description, order, creation_date, etc, while different rules can have the same of any of those.
        # for some reason, Reddit API stores many rules with the exact same created_utc
        # which means we can't track them, and therefore should drop them
        if latest_snap:
            if r['created_utc'] in sub_timestamps_latest[subname]:
                return False
            else:
                sub_timestamps_latest[subname].append(r['created_utc'])
        elif r['created_utc'] in sub_timestamps[subname]:
               return False
        elif r['created_utc'] in sub_timestamps[subname] and r['description'] in sub_descriptions[subname]: # this only happens for rules in the latest snapshot
            ## this rule is a candidate for a preexisting rule with a different short name
            candidate_rule_name = sub_rule_names[subname][ sub_timestamps[subname].index(r['created_utc']) ]
            candidate_rule = sub_rule_versions[subname][candidate_rule_name]
            cand_descs = [ v['description'] for v in candidate_rule]
            cand_violations = [ v['violation_reason'] for v in candidate_rule]
            cand_names = [ v['short_name'] for v in candidate_rule]
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
            sub_rule_versions[subname][ r['short_name'] ] = []
            sub_rule_names[subname].append( r['short_name'] )
            sub_timestamps[subname].append( r['created_utc'] )
            new_rule_count += 1
        sub_descriptions[subname].append( r['description'] )
    return effective_rname

def run_step0_mako(input_file, output_directory):
    global max_count
    global sub_count
    global sub_rule_versions
    global sub_rule_names
    global sub_descriptions
    global sub_timestamps 
    global sub_timestamps_latest
    global sub_metadata
    global sub_counter
    global earliest_drop_subs
    global latest_drop_subs

    global errors

    with lzma.open(input_file, mode='rt') as file:
        for i, line in enumerate(file):
            if i > max_count:
                break
            try:
                sub = json.loads(line)
            except:
                errors += 1
                continue
            subname = sub['subreddit'].lower()

            if sub_counter[subname] > 0: # skip duplicates
                continue
            if 'rules_earliest' in sub.keys() and 'rules' in sub['rules_earliest'].keys():
                if (('display_name' not in sub['meta_latest']['data'].keys()) # if second snapshot does not exist
                    or (len(sub['rules_earliest']['rules']) <= 0
                        and len(sub['rules_latest']['rules']) <= 0)): # or the sub does not have rules in either snap
                    continue
                elif (int(sub['meta_earliest']['data']['subscribers']) < 3   # or has fewer than 3 subscribers in both snaps
                    and int(sub['meta_latest']['data']['subscribers']) < 3):
                    continue
                elif (int(sub['meta_earliest']['data']['created_utc']) -    # or the sub was less than a month old
                    (datetime.strptime(sub['collection_metadata']['rules_earliest']['timestamp'], 
                                        '%Y-%m-%d %H:%M:%S')).timestamp()) < 60*60*24*30:  
                    continue                                                # we don't care about it 
                else:
                    sub_counter[subname] += 1 # NOTE: no sub gets this far...
            else:
                continue

            # get metadata
            sub_metadata[subname] = {}
            sub_metadata[subname]['subscribers_1'] = int(sub['meta_earliest']['data']['subscribers'])
            sub_metadata[subname]['subscribers_2'] = int(sub['meta_latest']['data']['subscribers'])
            sub_metadata[subname]['founding_date'] = sub['meta_earliest']['data']['created_utc']
            sub_metadata[subname]['earliest_scrape_date'] = sub['collection_metadata']['rules_earliest']['timestamp']
            sub_metadata[subname]['latest_scrape_date'] = sub['collection_metadata']['rules_latest']['timestamp']
            sub_metadata[subname]['num_rules_earliest'] = len(sub['rules_earliest']['rules'])
            sub_metadata[subname]['num_rules_latest'] = len(sub['rules_latest']['rules'])


            ## build structure up
            sub_rule_versions[subname] = {}
            sub_rule_names[subname] = []
            sub_descriptions[subname] = []
            sub_timestamps[subname] = []
            sub_timestamps_latest[subname] = []

            for r in sub['rules_earliest']['rules']:
                r = standardizeRule('earliest', sub, r, 
                                    (sub['collection_metadata']['rules_earliest']['timestamp']))
                effective_rname = getRuleName(r, subname)
                if effective_rname:
                    sub_rule_versions[subname][ effective_rname ].append( r )
                else:
                    earliest_drop_subs[subname] = sub_metadata[subname]
            
            for r in sub['rules_latest']['rules']:
                r = standardizeRule('latest', sub, r,
                                    (sub['collection_metadata']['rules_latest']['timestamp']))
                effective_rname = getRuleName(r, subname, True)
                if effective_rname:
                    sub_rule_versions[subname][ effective_rname ].append( r )
                else:
                    latest_drop_subs[subname] = sub_metadata[subname]
            sub_count += 1
            

    print('Finished processing scrapes')
    print(f'Total invalid subs: {len(earliest_drop_subs.keys())}')

    # for sub in drop_subs.keys(): # remove invalid subs
    #     if sub in sub_rule_versions.keys():
    #         sub_rule_versions.pop(sub)
    #         sub_metadata.pop(sub)

    # print(f'total valid subs:{len(sub_metadata.keys())}')

    min_creation = 1649388993
    max_creation = 0
    min_scrape_date = datetime.strptime('2024-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
    max_scrape_date = datetime.strptime('2010-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
    for sub in (earliest_drop_subs):
        creation = int(earliest_drop_subs[sub]['founding_date'])
        scrape = datetime.strptime(earliest_drop_subs[sub]['latest_scrape_date'], '%Y-%m-%d %H:%M:%S')
        if  creation < min_creation:
            min_creation = creation
        elif creation > max_creation:
            max_creation = creation
        if min_scrape_date > scrape:
            min_scrape_date = scrape
        elif max_scrape_date < scrape:
            max_scrape_date = scrape

    print(f'min creation:{datetime.utcfromtimestamp(min_creation)}, max creation:{datetime.utcfromtimestamp(max_creation)}')
    print(f'earliest scrape:{min_scrape_date}, latest scrape: {max_scrape_date}')

    valid_subs_in_invalid_timeframe = 0
    for sub in sub_metadata:
        late_scrape = datetime.strptime(sub_metadata[sub]['latest_scrape_date'], '%Y-%m-%d %H:%M:%S')
        if late_scrape > min_scrape_date and late_scrape < max_scrape_date:
            valid_subs_in_invalid_timeframe += 1
    print(f'valid subs with latest scrape within timeframe of invalid subs: {valid_subs_in_invalid_timeframe}')

    with open(f'{output_directory}/step0_rules_merged.json', 'w') as outfile:
        json.dump(sub_rule_versions, outfile)
    print( 'SCRIPT end' )


    header = ('communityID', 'subscribers_1', 'subscribers_2', 'founding_date', 'earliest_scrape_date',
            'latest_scrape_date', 'num_rules_earliest', 'num_rules_latest')
    with open(f'{output_directory}/sub_metadata_step_0.csv', 'w', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=header)
        writer.writeheader()
        for sub in sub_metadata:
            sub_data = sub_metadata[sub]
            data_out = {
                            'communityID' : sub
                            , 'subscribers_1' : sub_data['subscribers_1']
                            , 'subscribers_2' : sub_data['subscribers_2']
                            , 'founding_date' : sub_data['founding_date']
                            , 'earliest_scrape_date' : sub_data['earliest_scrape_date']
                            , 'latest_scrape_date' : sub_data['latest_scrape_date']
                            , 'num_rules_earliest' : sub_data['num_rules_earliest']
                            , 'num_rules_latest' : sub_data['num_rules_latest']
                        }
            writer.writerow(data_out)

    # output information about invalid subs
    with open(f'{output_directory}/drop_subs.csv', 'w', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=header)
        writer.writeheader()
        for sub in earliest_drop_subs:
            sub_data = earliest_drop_subs[sub]
            data_out = {
                            'communityID' : sub
                            , 'subscribers_1' : sub_data['subscribers_1']
                            , 'subscribers_2' : sub_data['subscribers_2']
                            , 'founding_date' : sub_data['founding_date']
                            , 'earliest_scrape_date' : sub_data['earliest_scrape_date']
                            , 'latest_scrape_date' : sub_data['latest_scrape_date']
                            , 'num_rules_earliest' : sub_data['num_rules_earliest']
                            , 'num_rules_latest' : sub_data['num_rules_latest']
                        }
            writer.writerow(data_out)


    print(f"errors: {errors}")

if __name__ == '__main__':
    input_data = 'c:/Users/nammy/Desktop/reddit-rule-change/original_data/subreddit_data_export-20230206.jsonl.xz'
    data_directory = 'c:/Users/nammy/Desktop/reddit-rule-change/output_data/mako'
    
    run_step0_mako(input_data, data_directory)

