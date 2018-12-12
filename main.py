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
from model import *


# This variable is to measure how long it took to execute the code
start_time=start_time = time.time()

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




df.to_csv('dataframe_output.csv', sep=',', encoding='utf-8',index=False)
# Percentage of matches with correct prediction from the rankings
print("Accuracy of ATP ranking for match outcome prediction: "+str(testRankingAccuracy(df,'WRank','LRank')))
print("Accuracy of ELO ranking for match outcome prediction: "+str(testRankingAccuracy(df,'elo_loser','elo_winner')))



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



######################################
# Model computation
# We use only a training set and do not use any validation set
# in fact, we use hte validation set only for the computation of hyper parameters - in actual data modelling, no validation is performed
# Then we test the matches of only ONE day.
# Then everyday we re-run our model training with the results of today's match as additional training data


features=pandas.read_csv("completed_dataframe.csv")
data=pandas.read_csv("dataframe_output.csv")

beg = data.Date.iloc[0]
end = data.Date.iloc[-1]

indices = data[(data.Date>=beg)&(data.Date<=end)].index
data.Date = data.Date.apply(lambda x:datetime.strptime(x, '%Y-%m-%d'))
data = data.iloc[indices,:].reset_index(drop=True)

#first day of testing set
start_date=data.Date.iloc[0]
#id of the first match of the testing set
test_beginning_match=data[data.Date==start_date].index[0] 
duration_val_matches=5

# The last day's matches are predicted - here we manually input the date for our test - should be 3 matches
today=datetime(2012,11,11)
first_test_matches=data[data.Date==today].index[0]
duration_test_matches=len(data)-first_test_matches

# length of training matches
training_length=len(data)-test_beginning_match-duration_test_matches-duration_val_matches


## Number of tournaments and players encoded directly in one-hot 
nb_players=50
nb_tournaments=5

## XGB hyper parameters
learning_rate=[0.295] 
max_depth=[19]
min_child_weight=[1]
gamma=[0.8]
csbt=[0.5]
lambd=[0]
alpha=[2]
num_rounds=[300]
early_stop=[5]
params=numpy.array(numpy.meshgrid(learning_rate,max_depth,min_child_weight,gamma,csbt,lambd,alpha,num_rounds,early_stop)).T.reshape(-1,9).astype(numpy.float)
xgb_params=params[0]

## We predict the confidence in each outcome, "duration_test_matches" matches at each iteration
print("Number of test matches: "+str(duration_test_matches))
print("Testing set of matches: \n"+str(data[data.Date>=today]))
conf=vibratingAssessStrategyGlobal(test_beginning_match,training_length,duration_val_matches,duration_test_matches,xgb_params,nb_players,nb_tournaments,features,data)
"""
for start in key_matches:
    conf=vibratingAssessStrategyGlobal(start,10400,duration_val_matches,duration_test_matches,xgb_params,nb_players,nb_tournaments,features,data)
    confs.append(conf)
confs=[el for el in confs if type(el)!=int]
conf=pd.concat(confs,0)
## We add the date to the confidence dataset (can be useful for analysis later)
dates=data.Date.reset_index()
dates.columns=["match","date"]
conf=conf.merge(dates,on="match")
conf=conf.sort_values("confidence0",ascending=False)
conf=conf.reset_index(drop=True)


## We store this dataset
conf.to_csv("../Generated Data/confidence_data.csv",index=False)

## Plot of ROI according to the % of matches we bet on
plotProfits(conf,"Test on the period Jan. 2013 -> March 2018")
"""
print(conf)

elapsed_time = time.time() - start_time
print("Done in :"+str(elapsed_time)+" seconds.")

