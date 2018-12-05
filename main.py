###############################################################
#
#
#			Tennis match betting algorithm
#
###############################################################

from dcm import *
from testfunctions import *

### TODO ### First we need to retrieve the latest data
#dataScrapper()

# We now clean the data and keep only the hyperparameters we need
df=dataCleaner()

# We compute the custom ranking:the period is currently 1 day as it is not taken into account at all
#df=glickoRanking(df, 1, 0.5)
df=compute_elo_rankings(df)

df.to_csv('dataframe_output.csv', sep=',', encoding='utf-8')

print(testRankingAccuracy(df,'WRank','LRank'))
print(testRankingAccuracy(df,'elo_loser','elo_winner'))
