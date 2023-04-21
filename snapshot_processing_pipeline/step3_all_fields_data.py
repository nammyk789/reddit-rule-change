""" 
take processed and labeled rule deltas and print them out in the form of a mostly blank csv
"""
import pandas as pd
import json
import csv

def get_all_fields_data(data_directory:str):
    header = ('name_change_type', 'description_change_type', 'violation_change_type', 
        'date_observed', 'timestamp_rule', 'communityID', 'ref', 'ruleID')
    with open(f'{data_directory}/step2_rules_processed.json', 'r', encoding='utf-8') as rules_file, open(f'{data_directory}/all_fields_data.csv','w', encoding='utf-8') as outfile:
        subs_all = json.load( rules_file )
        writer = csv.DictWriter(outfile, fieldnames=header)
        writer.writeheader()
        for i, (subname, subinfo) in enumerate(subs_all.items()):
            rules = subinfo['rules']
            for (rname, versions), p in zip(rules.items(), subinfo['rule_properties']):
                ### Build rows
                for j, r in enumerate(versions):
                    if j > 0: # so we don't double store each rule
                        continue

                    rule_out = {
                        'name_change_type' : p['name_change']
                        , 'description_change_type' : p['rule_change']
                        , 'violation_change_type' : p['violation_change']
                        , 'date_observed' : r['date_observed']
                        , 'timestamp_rule' : r['created_utc_date'] + '-01'
                        , 'communityID' : subname
                        , 'ref' : 'https://www.reddit.com/r/{}/'.format( subname )
                        , 'ruleID': r['rule_ID'] 
                    }
                    writer.writerow(rule_out)
    
    # add age in days of rule
    rules = pd.read_csv(f'{data_directory}/all_fields_data.csv')
    delta = pd.to_datetime(rules.date_observed) - pd.to_datetime(rules.timestamp_rule)
    rules['rule_age_in_days'] = delta.dt.days
    rules.to_csv(f'{data_directory}/all_fields_data.csv', index=False)

    # update sub metadata
    agg_data = pd.DataFrame(rules[['communityID', 'name_change_type']].groupby(['communityID', 'name_change_type']).agg(len)).reset_index()
    agg_data = agg_data.pivot(index='communityID', columns='name_change_type', values=0).fillna(0).reset_index()
    sub_metadata = pd.read_csv(f'{data_directory}/sub_metadata.csv')
    sub_metadata = agg_data.set_index('communityID').join(sub_metadata.set_index('communityID'), on=['communityID'])
    sub_metadata = sub_metadata.reset_index()
    sub_metadata.to_csv(f'{data_directory}/sub_metadata.csv')


if __name__ == "__main__":
    data_directory = 'c:/Users/nammy/Desktop/reddit-rule-change/output_data/seth'
    get_all_fields_data(data_directory)
