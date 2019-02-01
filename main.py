###############################################################
#
#
#			Tennis match betting algorithm
#
###############################################################

from dcm import *
from testfunctions import *
from datetime import *
from model import *
import time
from scraping_module import *

# Takes several arguments into input as options: if option not specified, will skip the step
# -s to enable scraping. By default scraps today's matches and tomorrow's
# -dc to do the data cleaning + compute elo rankings
# -df to compute the hyperparameters and create the dataframe
# -c to compute the model. By default computes today's and tomorrow's matches
# Example: python main.py -s -dc -df -c for the execution of everything

# This variable is to measure how long it took to execute the code
start_time = time.time()


if "-s" in sys.argv:
    ########################################################
    # First element is the start date for the scraping
    # Second element is the end date for the scraping
    # Date are inclusive

    # Variables for manual scraping
    #scrap_today=datetime(2019,1,15)
    #scrap_next_day=datetime(2019,1,15)

    # we usually only want the next day data
    day = date.today()
    scrap_today=datetime.combine(day, datetime.min.time())
    scrap_next_day=scrap_today+timedelta(days=1)

    # For ce the scrap for a specific url only - only works for ATP World Tour website!
    # eg. of input url: https://www.atptour.com/en/scores/current/australian-open/580/results
    #force_scrap=[['Australian Open','/en/scores/current/australian-open/580/results']]
    force_scrap=[]

    print("We scrap the following date range: "+scrap_today.strftime('%Y-%m-%d')+" - "+scrap_next_day.strftime('%Y-%m-%d'))

    if force_scrap!=[]:
        print('We scrap only the following tournaments:')
        for i in xrange(0,len(force_scrap)):
            print('Name: '+force_scrap[i][0])
    dataScrapper(scrap_today,scrap_next_day,force_scrap)


if "-dc" in sys.argv:
    ###############################################################
    # We now clean the data and keep only the hyperparameters we need
    df=dataCleaner()



    ####################################################################
    # We compute the custom ranking:the period is currently 1 day as it is not taken into account at all
    df=compute_elo_rankings(df)
    df=compute_elo2_rankings(df)
    #df=glickoRanking(df,7,0.1)

    ### Let's remove some unwanted matches, such as qualifying rounds - we use those only for a more accurate ELO ranking computation
    df=df[~df.Round.str.contains("Qualifying")]


    df.to_csv('dataframe_output.csv', sep=',', encoding='utf-8',index=False)
    # Percentage of matches with correct prediction from the rankings
    print("Accuracy of ATP ranking for match outcome prediction: "+str(testRankingAccuracy(df,'WRank','LRank')))
    print("Accuracy of Elo ranking for match outcome prediction: "+str(testRankingAccuracy(df,'elo_loser','elo_winner')))
    print("Accuracy of Elo2 ranking for match outcome prediction: "+str(testRankingAccuracy(df,'elo2_loser','elo2_winner')))
    #print("Accuracy of Glicko2 ranking for match outcome prediction: "+str(testRankingAccuracy(df,'glickoRK_loser','glickoRK_winner')))


if "-df" in sys.argv:
    #############################################
    # Generation of additional hyper parameters
    df=pandas.read_csv('dataframe_output.csv')

    #beg = datetime(2008,1,1) 
    beg = df.Date.iloc[0]
    end = df.Date.iloc[-1]

    indices = df[(df.Date>=beg)&(df.Date<=end)].index
    odds = df[["PSW","PSL"]]

    # Param based on past data (for a match, will look at the past x days except for the player where we check only the past 5 days)
    x = 150
    #print(indices)
    print("### Computing basic player data ###")
    features_player  = features_past_generation(features_player_creation,x,"playerft5",df,indices)
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

if "-c" in sys.argv:
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

    #first day of training set
    start_date=data.Date.iloc[0]
    train_beginning_match=data[data.Date==start_date].index[0]
    # this parameter should be at least 10% of the total training set in order to improve model accuracy
    # and reach faster convergence
    duration_val_matches=50

    # Loop to iteratively set the correct date for the test
    # The daterange function stops the day before the end date
    # we usually only want the next day data
    day = date.today()
    #start_testing_date=datetime.combine(day, datetime.min.time())
    #end_testing_date=start_testing_date+timedelta(days=1)
    
    start_testing_date=datetime(2017,12,31)
    end_testing_date=datetime(2018,11,19)
    #start_testing_date=datetime(2018,11,18)
    #end_testing_date=datetime(2018,11,19)


    result_set=[]
    for test_day in daterange(start_testing_date, end_testing_date):
        # The last day's matches are predicted - we choose all the matches that happened in the last day available in the dataframe
        # This logic implies that our dataframe is updated daily with the matches happening the next day
        
        # this check is in case there is a day in the dataset where no matches were played. if so, we skip this day
        if data[data.Date==(test_day)].empty:
            continue
        else:
            first_test_match=data[data.Date == test_day].index[0]
        #check if it is the last day of the table
        if (data[data.Date==(test_day+timedelta(1))].empty and test_day+timedelta(1)==end_testing_date):
            last_test_match=len(data)
            duration_test_matches= last_test_match - first_test_match
        else:
            # case where the next day in the dataset has no played matches . if so, we try to get the following day
            i = 1
            while data[data.Date==(test_day+timedelta(i))].empty:
                i += 1
            last_test_match=data[data.Date == (test_day+timedelta(i))].index[0]
            duration_test_matches= last_test_match - first_test_match

        # length of training matches
        training_length=last_test_match-train_beginning_match-duration_test_matches-duration_val_matches


        ## Number of tournaments and players encoded directly in one-hot 
        nb_players=50
        nb_tournaments=10

     ## XGB hyper parameters - original
        learning_rate=[0.295] 
        max_depth=[19]
        min_child_weight=[1]
        gamma=[0.8]
        csbt=[0.5]
        lambd=[0]
        alpha=[2]
        num_rounds=[300]
        early_stop=[5]
        params=np.array(np.meshgrid(learning_rate,max_depth,min_child_weight,gamma,csbt,lambd,alpha,num_rounds,early_stop)).T.reshape(-1,9).astype(np.float)
        xgb_params=params[0]

        ## XGB hyper parameters - modified
        #learning_rate=[0.305] 
        #max_depth=[20]
        #min_child_weight=[1]
        #gamma=[0]
        #csbt=[1]
        #lambd=[0]
        #alpha=[0]
        #num_rounds=[300]
        #early_stop=[5]
        #params=numpy.array(numpy.meshgrid(learning_rate,max_depth,min_child_weight,gamma,csbt,lambd,alpha,num_rounds,early_stop)).T.reshape(-1,9).astype(numpy.float)
        #xgb_params=params[0]

        ## We predict the confidence in each outcome, "duration_test_matches" matches at each iteration
        print("Matches day: "+str(test_day))
        print("Number of test matches: "+str(duration_test_matches))
        print("Testing set of matches: \n"+str(data[data.Date==test_day]))
        conf=vibratingAssessStrategyGlobal(first_test_match, training_length, duration_val_matches, duration_test_matches, xgb_params, nb_players, nb_tournaments, features, data)
        #print(conf)
        result_set.append(conf)

    print(result_set)
    result_set=[el for el in result_set if type(el)!=int]
    conf=pandas.concat(result_set,0)
    ## We add the date to the confidence dataset (can be useful for analysis later)
    dates=data.Date.reset_index()
    dates.columns=["match_index","date"]
    ## We add the player names to the confidence dataset (can be useful for analysis later)
    player1=data.Winner.reset_index()
    player1.columns=["match_index","Player1"]
    player2=data.Loser.reset_index()
    player2.columns=["match_index","Player2"]

    conf=conf.merge(dates,on="match_index")
    conf=conf.merge(player1,on="match_index")
    conf=conf.merge(player2,on="match_index")
    #conf=conf.sort_values("confidence",ascending=False)
    conf=conf.sort_values("date",ascending=False)
    conf=conf.reset_index(drop=True)
    #print(conf)
    conf.to_csv("result_data.csv",index=False)


#conf=pandas.read_csv("result_data.csv")
#ROI = profitComputation(1,conf)
#print("ROI for the dataset: "+str(ROI)+"%")
elapsed_time = time.time() - start_time
print("Done in :"+str(elapsed_time)+" seconds.")

