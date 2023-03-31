""" 
take processed and labeled rule deltas and print them out in the form of a mostly blank csv
"""
import pandas as pd
import json
import csv
from pprint import pprint
import nltk
from datetime import datetime
#nltk.download('punkt')

header = ('source', 'domain', 'lineID', 'change_type', 'before/after', 
        'timestamp', 'timestamp_rule', 'communityID', 'ref', 'ruleID', 'text')


def reddit_clean_text( rule_text):
    ### string handling
    rule_text = rule_text.replace(r'"', "'") # for reddit: lots of quotes to deal with
    #rule_text = rule_text.replace(r'\r', r'\n') # wierd newlines
    if rule_text.startswith('='): # excellhandling
        rule_text = '\\' + rule_text
    #assert '|' not in rule_text, rule_text + '\n' + "No |'s. if this triggers, comment out and add the replace line below" 
    rule_text = rule_text.replace(r'|', '/') # my coders use pipes so they can't appear in the data.
    #assert '\t' not in rule_text, rule_text.replace('\t', 'XXX') + '\n' + "if this triggers, comment out and add the replace line below" 
    rule_text = rule_text.replace('\t', '  ') # clean out tabs, which throw off csv cell ordering
    ### aiding tokenizer
    rule_text = rule_text.replace(r'.**', '. ') # for reddit: sentences followed by markdown
    rule_text = rule_text.replace(r'.*', '. ') # for reddit
    rule_text = rule_text.replace(r'\n\n**', '. ') # for reddit: double \n+bullets instead of .'s
    rule_text = rule_text.replace(r'\n\n*', '. ') # for reddit
    rule_text = rule_text.replace(r'\n\n-', '. ') # for reddit
    rule_text = rule_text.replace(r'.\n\n', '. ') # for reddit
    rule_text = rule_text.replace(r'\n\n', '. ') # for reddit
    rule_text = rule_text.replace('\n\n', '. ') # for reddit ### not sure why this catches things the above don't
    rule_text = rule_text.replace(r'\n**', '. ') # for reddit
    rule_text = rule_text.replace(r'\n*', '. ') # for reddit
    rule_text = rule_text.replace(r'\n', '. ') # for reddit
    rule_text = rule_text.replace('\n', '. ') # for reddit
    rule_text = rule_text.replace(r'\n', '. ') # for reddit
    rule_text = rule_text.replace('\n', '. ') # for reddit
    return( rule_text )

def step_3():
    with open('seth snapshot processing pipeline/step2_rules_processed.json', 'r', encoding='utf-8') as rules_file, open('output_data/seth_step3_rules.csv','w', encoding='utf-8') as outfile:
        subs_all = json.load( rules_file )
        writer = csv.DictWriter(outfile, fieldnames=header)
        writer.writeheader()
        template = {'codify_stage' : 'typol_redd_diff_20WQ', 'domain' : 'reddit'}
        for i, (subname, subinfo) in enumerate(subs_all.items()):
            rules = subinfo['rules']
            #print( subinfo.keys())
            for (rname, versions), p in zip(rules.items(), subinfo['rule_properties']):
                #p = subinfo['rule_properties']
                #print( rname, p['rule_name'] )
                sentences_seen =[]
                # PREP text (breakdown setences within versions and get uniqueness
                for j, r in enumerate(versions):
                    rule_text_full = reddit_clean_text(r['description'] )
                    r['rule_text_full'] = rule_text_full
                    r['rule_sentences'] = []
                    rule_texts = nltk.sent_tokenize( rule_text_full )
                    for rule in rule_texts:
                        if rule not in sentences_seen:
                            r['rule_sentences'].append( rule )
                            sentences_seen.append( rule )
                ### NOW build rows
                for j, r in enumerate(versions):
                    #print( r )
                    ### skip "unchanged" versions as eventually added or deleted or something, 
                    ##    unless that rul was never changed, then record one version of it 
                    if p['rule_change'] != 'unchanged' and r['rule_change'] == 'unchanged':
                        continue
                    elif p['rule_change'] == 'unchanged' and j > 0:
                        continue
                    ### or skip all unchanged rules
                    # if p['change'] != 'unchanged':
                    #     continue
                    rule_out = {
                          'source' : r['source']
                        , 'domain' : 'reddit'
                        , 'lineID' : r['priority']
                        , 'change_type' : p['rule_change']
                        , 'before/after' : r['rule_change']
                        , 'timestamp' : r['date_observed']
                        , 'timestamp_rule' : r['created_utc_date'].replace('-', '') + '01'
                        , 'communityID' : subname
                        , 'ref' : 'https://www.reddit.com/r/{}/'.format( subname )
                        , 'ruleID': r['rule_ID'] 
                        , 'text': r['rule_text_full']
                    }
                    writer.writerow(rule_out)
if __name__ == "__main__":
    step_3()