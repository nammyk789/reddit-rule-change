# Analyzing Rule Changes in Reddit Communities

This repository contains the work I did with Professor Seth Frey for my Masters project at U.C. Davis, 
and is a collaboration between the Communications department and the Computer Science department. We 
were working with two webscrapes of the entirety of Reddit taken 8 months apart, with the goal of analyzing 
rule change in subreddits. The repository is organized as follows:

`snapshot_processing_pipeline` contains all the code used to process the Reddit scrapes 
we were working in, organized into three steps. In order to process the data, simply run the 
`run_pipeline.py` file. The scrape data is not included in this repository because it was too large
to upload to GitHub, and needs to be added to the local repository before the pipeline is run.

`result_figures` contains all the figures generated in the Jupyter Notebooks that were included in my
final report

`jupyter notebooks` contains all the notebooks I used to analyze the processed subreddit-level and
rule-level data, including notebooks for training and testing classifiers and notebooks for 
visualizing the data and looking for patterns. These notebooks were used to generate the figures
and models used in my final writeup.

`data analysis.xlsx` is an Excel file with some metadata on the output of the processing pipeline,
along with more detailed notes on how rules were assigned labels.

Lastly, `reddit_rule_change_final_writeup.pdf` contains the report I turned in on the work in 
this repository.
