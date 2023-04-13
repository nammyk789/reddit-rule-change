from step0_preprocess_seth import *
from step0_preprocess_mako import *
from step1_clean import *
from step2_filter_rules import *
from step3_produce_name_data import *
from step3_produce_description_data import *
from step3_produce_violation_data import *


def run_seth_data():
    scrape_1_path = 'c:/Users/nammy/Desktop/reddit-rule-change/original_data/full_reddit_metadata_apr_23.jsonl'
    scrape_2_path = 'c:/Users/nammy/Desktop/reddit-rule-change/original_data/full_subreddit_metadata_dec_10.jsonl'
    data_directory = 'c:/Users/nammy/Desktop/reddit-rule-change/output_data/seth'

    print('STEP 0')
    run_step0_seth(scrape_1_path, scrape_2_path, data_directory)
    print('STEP 1')
    run_step1(data_directory)
    print('STEP 2')
    run_step2(data_directory)
    print('STEP 3')
    run_step3(data_directory)


def run_mako_data():
    input_data = 'c:/Users/nammy/Desktop/reddit-rule-change/original_data/subreddit_data_export-20230206.jsonl.xz'
    data_directory = 'c:/Users/nammy/Desktop/reddit-rule-change/output_data/mako'
    
    print('STEP 0')
    run_step0_mako(input_data, data_directory)
    print('STEP 1')
    run_step1(data_directory)
    print('STEP 2')
    run_step2(data_directory)
    print('STEP 3')
    run_step3(data_directory)


def run_step3(data_directory):
    run_step3_descriptions(data_directory)
    run_step3_names(data_directory)
    run_step3_violations(data_directory)


if __name__ == '__main__':
    print('RUNNING SETH DATA')
    run_seth_data()
    print('RUNNING MAKO DATA')
    run_mako_data()