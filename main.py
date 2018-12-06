###############################################################
#
#
#			Tennis match betting algorithm
#
###############################################################

from dcm import *
from testfunctions import *
from datetime import datetime,timedelta

########################################################
### TODO ### First we need to retrieve the latest data
#dataScrapper()



###############################################################
# We now clean the data and keep only the hyperparameters we need
df=dataCleaner()



####################################################################
# We compute the custom ranking:the period is currently 1 day as it is not taken into account at all
#df=glickoRanking(df, 1, 0.5)
df=compute_elo_rankings(df)




df.to_csv('dataframe_output.csv', sep=',', encoding='utf-8')
# Percentage of matches with correct prediction from the rankings
print("Accuracy of ATP ranking for match outcome prediction: "+str(testRankingAccuracy(df,'WRank','LRank')))
print("Accuracy of ELO ranking for match outcome prediction: "+str(testRankingAccuracy(df,'elo_loser','elo_winner')))



#############################################
# Generation of additional hyper parameters

beg = datetime(2008,1,1) 
#beg = df.Date.iloc[0]
end = df.Date.iloc[-1]
indices = df[(df.Date>beg)&(df.Date<=end)].index


# Param based on past data (for a match, will look at the past x days except for the player where we check only the past 5 days)
x = 150
print("### Computing basic player data ###")
features_player  = features_past_generation(features_player_creation,5,"playerft5",df,indices)
print("### Computing basic match data ###")
features_h2h     = features_past_generation(features_duo_creation,x,"h2hft",df,indices)
print("### Computing recent data about matches ###")
features_general = features_past_generation(features_general_creation,x,"generalft",df,indices)
print("### Computing basic player data ###")
features_recent  = features_past_generation(features_recent_creation,x,"recentft",df,indices)


print("Done!")