###############################################################
#
#
#			Tennis match betting algorithm
#
###############################################################

from dcm import *
from testfunctions import *
from datetime import *
import time

# This variable is to measure how long it took to execute the code
start_time=start_time = time.time()

########################################################
### TODO ### First we need to retrieve the latest data
#dataScrapper()

"""

###############################################################
# We now clean the data and keep only the hyperparameters we need
df=dataCleaner()



####################################################################
# We compute the custom ranking:the period is currently 1 day as it is not taken into account at all
#df=glickoRanking(df, 1, 0.5)
df=compute_elo_rankings(df)




df.to_csv('dataframe_output.csv', sep=',', encoding='utf-8',index=False)
# Percentage of matches with correct prediction from the rankings
print("Accuracy of ATP ranking for match outcome prediction: "+str(testRankingAccuracy(df,'WRank','LRank')))
print("Accuracy of ELO ranking for match outcome prediction: "+str(testRankingAccuracy(df,'elo_loser','elo_winner')))

"""

#############################################
# Generation of additional hyper parameters
df=pandas.read_csv('dataframe_output.csv')

beg = datetime(2008,1,1) 
beg = df.Date.iloc[0]
end = df.Date.iloc[-1]
indices = df[(df.Date>beg)&(df.Date<=end)].index
odds = df[["PSW","PSL"]]

# Param based on past data (for a match, will look at the past x days except for the player where we check only the past 5 days)
x = 150
print("### Computing basic player data ###")
features_player  = features_past_generation(features_player_creation,5,"playerft5",df,indices)
print("### Computing basic match data ###")
features_h2h     = features_past_generation(features_h2h_creation,x,"h2hft",df,indices)
print("### Computing recent data about matches ###")
features_general = features_past_generation(features_general_creation,x,"generalft",df,indices)
print("### Computing basic player data ###")
features_recent  = features_past_generation(features_recent_creation,x,"recentft",df,indices)

features_categorical = df[["Series","Court","Surface","Round","Best of","Tournament"]]
features_categorical_encoded = categorical_features_encoding(features_categorical)
players_encoded = features_players_encoding(df)
tournaments_encoded = features_tournaments_encoding(df)
features_onehot = pandas.concat([features_categorical_encoded,players_encoded,tournaments_encoded],1)

############################### 
# Duplication of rows
## For the moment we have one row per match. 
## We "duplicate" each row to have one row for each outcome of each match. 
## Of course it isn't a simple duplication of  each row, we need to "invert" some features

# Elo data
elo_rankings = df[["elo_winner","elo_loser","proba_elo"]]
elo_1 = elo_rankings
elo_2 = elo_1[["elo_loser","elo_winner","proba_elo"]]
elo_2.columns = ["elo_winner","elo_loser","proba_elo"]
elo_2.proba_elo = 1-elo_2.proba_elo
elo_2.index = range(1,2*len(elo_1),2)
elo_1.index = range(0,2*len(elo_1),2)
features_elo_ranking = pandas.concat([elo_1,elo_2]).sort_index(kind='merge')

# Categorical features
features_onehot = pandas.DataFrame(numpy.repeat(features_onehot.values,2, axis=0),columns=features_onehot.columns)

# odds feature
features_odds = pandas.Series(odds.values.flatten(),name="odds")
features_odds = pandas.DataFrame(features_odds)

### Building of the final dataset
# You can remove some features to see the effect on the ROI
features = pandas.concat([features_odds,
                  features_elo_ranking,
                  features_onehot,
                  features_player,
                  features_h2h,
                  features_general,
                  features_recent],1)

features.to_csv("completed_dataframe.csv",index=False)

elapsed_time = time.time() - start_time
print("Done in :"+str(elapsed_time)+" seconds.")