<!--
To run in terminal:
pweave -f pandoc writeup.pmd
pandoc -s --mathjax writeup.md -o writeup.html 
-->

# Analysis of Rule Changes in Subreddits

Namrata Kasaraneni



## Data
All of the figures generated in this plot uses data taken from two snapshots of Reddit: 
the first was scraped in April 2020, and the second was scraped December of 2020. Subreddits 
that had fewer than three subscribers in both scrapes, zero rules in both scrapes, or that were 
founded within a month of the first scrape were filtered out. With the remaining
subs, we tracked how rules changed between the two snapshots. We identified rules that
were the same if they had the same creation timestamp and description, or the same rule 
name.There were five types of text labels:

1. **unchanged**: Rules that had fewer than 10 characters change between snapshots, or rules
    that were present at the subreddit's creation and were present in the second snapshot.
2. **added**: Rules that was added after the subreddit's creation or after the first snapshot.
3. **deleted**: Rules that were present in the first snapshot and not the second.
4. **changed**: Rules that were present at the creation of the subreddit, and then changed
    between the first and second snapshot.
5. **change-added**: Rules that were added after the creation of the subreddit, and were then changed   
    between the first and second snapshot.

Additionally, each rule had a short name (the name displayed on the subreddit's main page) and 
a violation reason (which moderators use to flag posts that violate the rules). Similar text 
analysis was done on the short names and the violation reasons of each rule.

### Description of the dataset




The datasets contain 358026 subs. The subs have between 1
to 25 rules, with the first and third quartiles being 2
and 5 rules. 

## Growth in Rules Corpus


![Figure 1](figures/writeup_figure3_1.png){width=400}

**Figure 1** is a histogram that summarizes the change types of all the rules we processed between
the two snapshots. The vast majority of rules were unchanged between the snapshots. Out of the ones 
that were altered, addition was by far the most frequent type of rule alteration, followed by addition.
Actual change of the rule description is the rarest type of rule alteration. **Figure 1** indicates that
the overall corpus of subreddit rules is increasing over time. 

## Difference in Changes Between Text Fields




In the table below, we can compare the percentage of different change types between rule names,
rule descriptions, and rule violation reasons. Each row contains the average percentage of the 
change type that was applied to the text field in each sub. For example, the first entry in the
table, corresponding to the column **Rule Name** and the row **unchanged**, says that on average,
each sub left 94.08% of its rule names unchanged. 

### Average Rule Changes for Each Text Field 

| Change Type &nbsp;&nbsp;&nbsp;&nbsp;| Rule Name &nbsp;&nbsp;&nbsp;&nbsp;| Rule Description &nbsp;&nbsp;&nbsp;&nbsp;| Violation Reason &nbsp;&nbsp;|
| -- | :--: | :--: | :--: |
| **unchanged** | 94.08% | 93.75% | 90.41% |
| **added** | 5.26% | 5.18% | 8.66% |
| **deleted** | 0.6% | 0.6% | 0.8% |
| **changed** | 0.04% | 0.37% | 0.11% |
| **change-added** | 0.01% | 0.09% | 0.02% |

We can see that the rule descriptions change significantly more often than violation reasons 
or rule names. Violation reasons are added more often than rule names or rule descriptions and
are the least likely to be left unchanged, suggesting that there is more churn with violation 
reasons. 


## Punctuated Equilibrium


![Figure 2](figures/writeup_figure5_1.png){width=400}


**Figure 2** shows a histogram of the percent of rules altered (by either adding, deleting, 
or changing their rules) for each sub, with subs that left all of their rules unchanged filtered out. 
We can see evidence for punctuated equilibrium in the significant number of subs that had over 60% 
of their rules altered. In total, 697 
subs changed at least 60% of their rules between the two snapshots. 
230 of those subs altered 90-100% of their rules.


![Figure 3](figures/writeup_figure6_1.png){width=400}

**Figure 3** is a similar histogram, but only showing rules that had their descriptions changed, discounting 
rules that were added or deleted. The evidence has the caveat that subs with high percentages of rule changes 
or alterations might in reality have a low count of rules, amplifying the perceived turnover. 
