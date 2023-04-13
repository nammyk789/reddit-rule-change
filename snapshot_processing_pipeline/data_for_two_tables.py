""" 
take processed and labeled rule deltas and print them out in the form of a mostly blank csv
"""
import pandas as pd
import json
import csv
from pprint import pprint
import nltk
from datetime import datetime

def get_added_or_deleted_rules_data(data_directory:str):
    header = ('source', 'name_change_type', 'description_change_type', 'violation_change_type', 
        'timestamp', 'timestamp_rule', 'communityID', 'ref', 'ruleID')
    with open(f'{data_directory}/step2_rules_processed.json', 'r', encoding='utf-8') as rules_file, open(f'{data_directory}/added_or_deleted_rules_data.csv','w', encoding='utf-8') as outfile:
        subs_all = json.load( rules_file )
        writer = csv.DictWriter(outfile, fieldnames=header)
        writer.writeheader()
        for i, (subname, subinfo) in enumerate(subs_all.items()):
            rules = subinfo['rules']
            for (rname, versions), p in zip(rules.items(), subinfo['rule_properties']):
                if p['name_change'] != 'added' and p['name_change'] != 'deleted':
                    continue
                ### Build rows
                for j, r in enumerate(versions):
                    if j > 0: # so we don't double store each rule
                        continue

                    rule_out = {
                          'source' : r['source']
                        , 'name_change_type' : p['name_change']
                        , 'description_change_type' : p['rule_change']
                        , 'violation_change_type' : p['violation_change']
                        , 'timestamp' : r['date_observed']
                        , 'timestamp_rule' : r['created_utc_date'].replace('-', '') + '01'
                        , 'communityID' : subname
                        , 'ref' : 'https://www.reddit.com/r/{}/'.format( subname )
                        , 'ruleID': r['rule_ID'] 
                    }
                    writer.writerow(rule_out)

def get_rules_in_both_snaps_data(data_directory:str):
    header = ('source', 'name_change_type', 'description_change_type', 'violation_change_type', 
        'timestamp', 'timestamp_rule', 'communityID', 'ref', 'ruleID')
    with open(f'{data_directory}/step2_rules_processed.json', 'r', encoding='utf-8') as rules_file, open(f'{data_directory}/rules_in_both_snaps_data.csv','w', encoding='utf-8') as outfile:
        subs_all = json.load( rules_file )
        writer = csv.DictWriter(outfile, fieldnames=header)
        writer.writeheader()
        for i, (subname, subinfo) in enumerate(subs_all.items()):
            rules = subinfo['rules']
            for (rname, versions), p in zip(rules.items(), subinfo['rule_properties']):
                if not (p['rule_present_in_earliest_scrape'] and p['rule_present_in_latest_scrape']):
                    continue
                ### Build rows
                for j, r in enumerate(versions):
                    if j > 0: # so we don't double store each rule
                        continue

                    rule_out = {
                          'source' : r['source']
                        , 'name_change_type' : p['name_change']
                        , 'description_change_type' : p['rule_change']
                        , 'violation_change_type' : p['violation_change']
                        , 'timestamp' : r['date_observed']
                        , 'timestamp_rule' : r['created_utc_date'].replace('-', '') + '01'
                        , 'communityID' : subname
                        , 'ref' : 'https://www.reddit.com/r/{}/'.format( subname )
                        , 'ruleID': r['rule_ID'] 
                    }
                    writer.writerow(rule_out)


if __name__ == "__main__":
    data_directory = 'c:/Users/nammy/Desktop/reddit-rule-change/output_data/seth'
    get_added_or_deleted_rules_data(data_directory)
    get_rules_in_both_snaps_data(data_directory)