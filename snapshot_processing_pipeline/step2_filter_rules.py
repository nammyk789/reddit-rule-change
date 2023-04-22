"""
go through rules and pull out those that never changed

QUESTION: Are we only keeping rules that changed, or subs that had at least one change?
"""
import json
import datetime
from pprint import pprint
import collections
from numpy import diff

# filepaths
rules_file = 'seth snapshot processing pipeline/step1_rules_cleaned.json'
metadata_file = 'seth snapshot processing pipeline/step1_rules_metadata.json'
### helpers
def generate_version_properties( versions, metadata, i):
    props = {}
    descs = [ v['description'] for v in versions ]
    names = [ v['short_name'] for v in versions ]
    props['num_rule_versions'] = len(versions)
    props['rule_present_at_creation'] = metadata['rules_present_at_creation'][i] # rule present at subs creation
    props['rule_present_in_earliest_scrape'] = metadata['rules_present_in_earliest_scrape'][i]
    props['rule_present_in_latest_scrape'] = metadata['rules_present_in_latest_scrape'][i]
    props['descriptions_distance'] = metadata['rules_description_distance'][i]
    props['violation_distance'] = metadata['rules_violation_reason_distance'][i]
    props['name_distance'] = metadata['rules_short_name_distance'][i]
    props['descriptions_unchanged'] = (1 == len(set(descs))) # also true if only present at creation
    props['name_unchanged'] = (1 == len(set(names)))

    # we don't care about descriptions that are set to the defaults, so filter them out
    props['num_description_versions'] = 0
    props['description_present_in_earliest_scrape'] = False
    props['description_present_in_latest_scrape'] = False
    for v in versions:
        v['description_exists'] = False
        if v['description'] not in [None, v['short_name'], '']:
            v['description_exists'] = True
            props['num_description_versions'] += 1
            if v['source'] == 'earliest':
                props['description_present_in_earliest_scrape'] = True
            else:
                props['description_present_in_latest_scrape'] = True


    # we don't care about violation reasons that are set to the defaults, so filter them out
    props['num_violation_versions'] = 0
    props['violation_present_in_earliest_scrape'] = False
    props['violation_present_in_latest_scrape'] = False
    props['violation_change'] = None
    for v in versions:
        v['violation_exists'] = False
        if v['violation_reason'] not in [None, v['short_name'], '']:
            v['violation_exists'] = True
            props['num_violation_versions'] += 1
            if v['source'] == 'earliest':
                props['violation_present_in_earliest_scrape'] = True
            else:
                props['violation_present_in_latest_scrape'] = True
    return( props )

def run_step2(data_directory:str):
    with open(f'{data_directory}/step1_rules_cleaned.json', 'r') as rules_file, open(f'{data_directory}/step1_rules_metadata.json', 'r') as metadata_file:
        rules_all = json.load( rules_file )
        metadata_all = json.load(  metadata_file )
        print( "num subs total:", len( rules_all ) )
        
        sub_count = 0  # keep track of how many subs we have iterated through
        
        effects = collections.Counter()
        for subname, rules in rules_all.items(): # this loop is successfully hitting every sub
            sub_count += 1
            metadata = metadata_all[ subname ]
            metadata['rule_properties'] = []
            # did the description in the rule ever change?
            for i, (rname, versions) in enumerate(rules.items()): # is rules.items() actually iterable?
                ### BUILD
                ### easily testable rule properties
                # print(metadata['rules_version_distance'][i])
                p = generate_version_properties( versions, metadata, i )
                p['subname'] = subname 
                p['rule_name'] = rname
                metadata['rule_properties'].append( p )
                
                ###TEST UNCHANGED
                # IF versions exist for identical form in all scrapes
                #         description is equal in all versions
                #         OR exists in near-identical form in all scrapes
                #             description is levenshtein equal in all versions
                #     all creation dates are in the subs founding batch 
                #     AND versions exist for all scrapes (has 2 versions (at least one early) or 3 versions (at least one late))
                #         (possible num of versions: 2, 3)
                # simple exp: if rule is present in reddit, was present at creation, and is unchanged, mark it unchanged
                if (
                    p['num_description_versions'] > 1
                    and ( # description basically the same
                        p['descriptions_unchanged']
                        or
                        p['descriptions_distance'] < 10
                    )
                ):
                    effects['rule_unchanged'] += 1
                    p['rule_change'] = 'unchanged'
                    for v in versions:
                        v['rule_change'] = 'unchanged'
                
                ###TEST DELETED
                # AND doesnt exist in later scrapes
                #     doesnt have  3 versions
                #         (possible num of versions: 1, 2)
                #     has at least one early version
                #     doesnt have a late version
                # all creation dates are in the subs founding batch
                # IF versions exist for identical form in all scrapes
                #         description is equal in all versions
                #         OR exists in near-identical form in all scrapes
                #             description is levenshtein equal in all versions
                # simple: if rule is in early but not late, present at creation, and unchanged, mark it deleted
                elif (
                    (not p['description_present_in_latest_scrape'])
                    and p['num_description_versions'] == 1
                ):
                    effects['deleted'] += 1
                    p['rule_change'] = 'deleted'
                    for v in versions:
                        v['rule_change'] = 'unchanged'
                    versions[-1]['rule_change'] = 'deleted'
                    if p['num_description_versions'] == 2:
                        if not ( int(versions[0]['date_observed']) <= int(versions[1]['date_observed'] ) ):
                            print()
                            print( rname )
                            pprint( p )
                            pprint( versions )

                ###TEST ADDED
                # AND any scrapes that are missing are first scrapes
                # no version creation dates are in the subs founding batch
                #     (fewer constraints because there could be three versions if first 
                #         (possible num of versions: 1, 2, 3)
                #     scrape was way after rule creation, which was way after first rule addtiion)
                # IF versions exist for identical form in all scrapes
                #         description is equal in all versions
                #         OR exists in near-identical form in all scrapes
                #             description is levenshtein equal in all versions
                elif (
                    p['description_present_in_latest_scrape']
                    and p['num_description_versions'] == 1
                ):
                    assert( not 'rule_change' in p )
                    if not p['description_present_in_latest_scrape']:
                        effects['added_deleted'] += 1
                        p['rule_change'] = 'deleted'
                        versions[0]['rule_change'] = 'deleted'
                        assert( p['num_description_versions'] == 1 )
                    else:
                        effects['added'] += 1
                        p['rule_change'] = 'added'
                        for v in versions:
                            v['rule_change'] = 'unchanged'
                        versions[0]['rule_change'] = 'added'
                
                ###TEST CHANGE
                        # AND versions exist for all scrapes (has 2 versions (at least one early) or 3 versions (at least one late))
                        # all creation dates are in the subs founding batch
                        #     (possible num of versions: 2, 3)
                        # IF description  difference is large (enough)
                        # DO:
                        #     if two versions:
                        #         label first 'before' and second 'after'
                        #     if three versions NOTE: this hasn't been implemented yet
                        #         [pop, before, after] # if 1 and 2 are the same, trivial difference
                        #         [before, pop, after] # if 1 and 2 are the same, no difference
                        #         [before, after, pop] # if 2 and 3 are the same
                        #         OR
                        #         [before, before, after] #if all three are different
                elif (
                    p['num_description_versions'] > 1
                    and (
                        not p['descriptions_unchanged']
                        and
                        p['descriptions_distance'] >= 10
                    )
                ):
                    effects['changed'] += 1
                    if p['num_description_versions'] == 2:
                        p['rule_change'] = 'changed'
                        versions[0]['rule_change'] = 'before'
                        versions[1]['rule_change'] = 'after'
                
                elif p['num_description_versions'] == 0:
                    effects['never_present'] += 1
                    p['rule_change'] = 'never_present'
                    for v in versions:
                        v['rule_change'] = 'never_present'


                
                # NAME CHANGE TESTS            
                # two versions exist and names are unchanged
                if (
                    ( # rule is present in reddit
                        p['num_rule_versions'] > 1
                    )
                    and ( # description basically the same
                        p['name_distance'] < 10
                        or p['name_unchanged']
                    )
                ):
                    if p['rule_change'] == 'deleted':
                        pass
                    p['name_change'] = 'unchanged'
                    for v in versions:
                        v['name_change'] = 'unchanged'
                
                # name was deleted
                elif (
                    p['num_rule_versions'] < 2 
                    and not p['rule_present_in_latest_scrape']
                ):
                    p['name_change'] = 'deleted'
                    for v in versions:
                        v['name_change'] = 'unchanged'
                    versions[-1]['name_change'] = 'deleted'

                # name was added
                elif (
                    ( p['rule_present_in_latest_scrape']
                        or p['num_rule_versions'] == 1
                    )
                    and (
                        p['name_distance'] < 10
                        or p['num_rule_versions'] == 1
                    )
                ):
                    if not p['rule_present_in_latest_scrape']:
                        p['name_change'] = 'deleted'
                        versions[0]['name_change'] = 'deleted'
                    else:
                        p['name_change'] = 'added'
                        for v in versions:
                            v['name_change'] = 'unchanged'
                        versions[0]['name_change'] = 'added'
                
                # name was changed
                elif (
                    p['num_rule_versions'] > 1
                    and p['name_distance'] >= 10
                ):
                    p['name_change'] = 'changed'
                    versions[0]['name_change'] = 'before'
                    versions[-1]['name_change'] = 'after'
                

                # VIOLATION REASON CHANGE TESTS
                # violation reasons are unchanged
                if (p['num_violation_versions'] > 1
                    and p['violation_distance'] < 5
                ):
                    p['violation_change'] = 'unchanged'
                    for v in versions:
                        v['violation_change'] = 'unchanged'
                
                # violation reason is deleted
                elif (
                    p['num_violation_versions'] == 1 
                    and not p['violation_present_in_latest_scrape']
                ):
                    p['violation_change'] = 'deleted'
                    for v in versions:
                        v['violation_change'] = None
                    versions[0]['violation_change'] = 'deleted'
                
                # violation is added
                elif (
                    p['num_violation_versions'] == 1 
                    and not p['violation_present_in_earliest_scrape']
                ):

                    p['violation_change'] = 'added'
                    for v in versions:
                        v['violation_change'] = None
                    versions[0]['violation_change'] = 'added'
                        
                
                # violation is changed
                elif (
                    p['num_violation_versions'] == 2
                    and p['violation_distance'] >= 5
                ):
                    p['violation_change'] = 'changed'
                    versions[0]['violation_change'] = 'before'
                    versions[-1]['violation_change'] = 'after'
                
                else:
                    p['violation_change'] = 'never_present'
                    for v in versions:
                        v['violation_change'] = 'never_present'


        ### TEST
        # check for catastrophes (all rules changed)
        #TODO: Change to continuous measure
        #   calculate proportion of rules that changed, added, deleted, or unchanged
        #   if proportions doesn't work, do counts
        catastrophe_add_or_delete = 0 
        catastrophe_changes = 0
        is_catastrophe = False
        for subname, rules in rules_all.items():
            metadata = metadata_all[ subname ] # creates pointer, not copy
            if all([p['name_change'] in ('deleted', 'added') for p in metadata['rule_properties']]):
                catastrophe_add_or_delete += 1
                is_catastrophe = True
            if all([p['name_change'] in ('changed') for p in metadata['rule_properties']]):
                catastrophe_changes += 1
                is_catastrophe = True
            if is_catastrophe:
                metadata['catastrophe'] = True
        
        ### WRAP IT UP
        d_unaccounted_for = 0
        d_accounted_for = 0
        version_change_types = collections.Counter()
        for subname, rules in rules_all.items():
            for j, (rname, versions) in enumerate(rules.items()):
                for i, v in enumerate(versions):
                    # v["rule_id"] = f"{subname}_{j}"
                    flag = False
                    if 'rule_change' not in v:
                        d_unaccounted_for += 1
                        flag = True
                    if 'rule_change' in v:
                        d_accounted_for += 1
                        version_change_types[v['rule_change']] += 1
                    if flag:
                        print("\nRULE unaccounted for")
                        print(subname, rname, j)
                        pprint(versions)
                        pprint( generate_version_properties( versions, metadata_all[ subname ], j ) )
                        

    print(f"rules accounted for: {d_accounted_for}")
    print(f"rules still unaccounted for: {d_unaccounted_for}")
    print(f"rules that were unchanged: {effects['rule_unchanged']}")
    print(f"rules that were added: {effects['added']}")
    print(f"rules that were deleted: {effects['deleted']}")
    print(f"rules that were changed: {effects['changed']}")
    print(f"rules that were never present: {effects['never_present']}")
    print(f"subs that added or deleted every rule: {catastrophe_add_or_delete}")
    print(f"subs that changed every rule: {catastrophe_changes}")

    ### BUILD
    ### before writing, merge all rules into metadata object, and just write that
    for subname, rules in rules_all.items():
        metadata_all[ subname ]['rules'] = rules

    with open(f'{data_directory}/step2_rules_processed.json', 'w') as outfile:
        print( 'outputting metadata' )
        json.dump(metadata_all, outfile)

if __name__ == '__main__':
    data_directory = 'c:/Users/nammy/Desktop/reddit-rule-change/output_data/seth'
    run_step2(data_directory)