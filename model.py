import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import *
import matplotlib.pyplot as plt

############################### STRATEGY ASSESSMENT ############################
### the following functions are used to make the predictions and compute the ROI

def xgbModelBinary(xtrain,ytrain,xval,yval,p,sample_weights=None):
    """
    XGB model training. 
    Early stopping is performed using xval and yval (validation set).
    Outputs the trained model, and the prediction on the validation set
    """
    if sample_weights==None:
        dtrain=xgb.DMatrix(xtrain,label=ytrain)
    else:
        dtrain=xgb.DMatrix(xtrain,label=ytrain,weight=sample_weights)
    if xval.empty:
        eval_set = [(dtrain, "train_loss")]
    else:
        dval=xgb.DMatrix(xval,label=yval)
        eval_set = [(dtrain,"train_loss"),(dval, 'eval')]
    params={'eval_metric':"logloss","objective":"binary:logistic",'subsample':0.8,
            'min_child_weight':p[2],'alpha':p[6],'lambda':p[5],'max_depth':int(p[1]),
            'gamma':p[3],'eta':p[0],'colsample_bytree':p[4]}
    model=xgb.train(params, dtrain, int(p[7]),evals=eval_set,early_stopping_rounds=int(p[8]),verbose_eval=0)
    return model

def xgbModelBinaryCV(xtrain,ytrain,xval,yval,p,sample_weights=None):
    """
    XGB model CV training. 
    Early stopping is performed using xval and yval (validation set).
    Outputs the trained model, and the prediction on the validation set
    """
    xtrain=pd.concat([xtrain,xval])
    ytrain=pd.concat([ytrain,yval])
    if sample_weights==None:
        dtrain=xgb.DMatrix(xtrain,label=ytrain)
    else:
        dtrain=xgb.DMatrix(xtrain,label=ytrain,weight=sample_weights)
    if xval.empty:
        eval_set = [(dtrain, "train_loss")]
    else:
        dval=xgb.DMatrix(xval,label=yval)
        eval_set = [(dtrain,"train_loss"),(dval, 'eval')]
    params={'eval_metric':"logloss","objective":"binary:logistic",'subsample':0.8,
            'min_child_weight':p[2],'alpha':p[6],'lambda':p[5],'max_depth':int(p[1]),
            'gamma':p[3],'eta':p[0],'colsample_bytree':p[4]}
    cv_outcome=xgb.cv(params, dtrain, int(p[7]),seed=5,nfold=10,early_stopping_rounds=int(p[8]),metrics={'mae'})
    return cv_outcome


def assessStrategyGlobal(test_beginning_match,
                         duration_train_matches,
                         duration_val_matches,
                         duration_test_matches,
                         xgb_params,
                         nb_players,
                         nb_tournaments,
                         features,
                         data,
                         weights,
                         model_name="0"
                         ):
    """
    Given the id of the first match of the testing set (id=index in the dataframe "data"),
    outputs the confidence dataframe.
    The confidence dataframe tells for each match is our prediction is right, and for
    the outcome we chose, the confidence level.
    The confidence level is simply the probability we predicted divided by the probability
    implied by the bookmaker (=1/odd).
    """
    ########## Training/validation/testing set generation
    
    # Number of matches in our dataset (ie. nb. of outcomes divided by 2)
    nm=int(len(features)/2)
    
    # Id of the first and last match of the testing,validation,training set
    beg_test=test_beginning_match
    end_test=min(test_beginning_match+duration_test_matches-1,nm-1)
    if duration_val_matches==0:
        end_val=0
        beg_val=0
    else:
        end_val=min(beg_test-1,nm-1)
        beg_val=beg_test-duration_val_matches
    end_train=beg_val-1
    beg_train=beg_val-duration_train_matches
       
    train_indices=range(2*beg_train,2*end_train+2)
    if duration_val_matches == 0:
        val_indices=range(0)
    else:
        val_indices=range(2*beg_val,2*end_val+2)
    test_indices=range(2*beg_test,2*end_test+2)
    
    if (len(test_indices)==0)|(len(train_indices)==0):
        return 0
    
    # Split in train/validation/test
    xval=features.iloc[val_indices,:].reset_index(drop=True)
    xtest=features.iloc[test_indices,:].reset_index(drop=True)
    xtrain=features.iloc[train_indices,:].reset_index(drop=True)
    ytrain=pd.Series([1,0]*int(len(train_indices)/2))
    yval=pd.Series([1,0]*int(len(val_indices)/2))
    
    # We limit the number of players and tournaments one-hot encoded : we'll keep only the 
    # players that won the most matches to avoid overfitting and make the process quicker
    # Biggest players :
    biggest_players=data.iloc[range(beg_train,end_train),:][["Winner","Loser"]]
    biggest_players=pd.concat([biggest_players.Winner,biggest_players.Loser],0)
    biggest_players=list(biggest_players.value_counts().index[:nb_players])
    player_columns=[el for el in xtrain.columns if el[:6]=="player"]
    to_drop_players=[el for el in player_columns if el[7:] not in biggest_players]
    # Biggest Tournaments
    biggest_tournaments=data.iloc[range(beg_train,end_train),:]["Tournament"]
    biggest_tournaments=list(biggest_tournaments.value_counts().index[:nb_tournaments])
    tournament_columns=[el for el in xtrain.columns if el[:10]=="tournament"]
    to_drop_tournaments=[el for el in tournament_columns if el[11:] not in biggest_tournaments]
    # We drop smallest Tournaments and players
    xtrain=xtrain.drop(to_drop_players+to_drop_tournaments,1)
    xval=xval.drop(to_drop_players+to_drop_tournaments,1)
    xtest=xtest.drop(to_drop_players+to_drop_tournaments,1)
    
    ### ML model training
    #print(xval)
    #print(yval)
    model=xgbModelBinary(xtrain,ytrain,xval,yval,xgb_params,sample_weights=weights)
    #xgb.plot_importance(model, max_num_features=10)
    #plt.show()
    ### ML model assessment
    #cv_output=xgbModelBinaryCV(xtrain,ytrain,xval,yval,xgb_params,sample_weights=None)
    #print("Mean Absolute Error: "+str(cv_output['test-mae-mean'].min()))
    #cv_output.to_csv("cv_data.csv",index=False)

    # The probability given by the model to each outcome of each match :
    pred_test= model.predict(xgb.DMatrix(xtest,label=None)) 
    # For each match, the winning probability the model gave to the players that won (should be high...) :
    prediction_test_winner=pred_test[range(0,len(pred_test),2)]
    # For each match, the winning probability the model gave to the players that lost (should be low...) :
    prediction_test_loser=pred_test[range(1,len(pred_test),2)]
    
    ### Odds and predicted probabilities for the testing set (1 row/match)
    odds=data[["PSW","PSL"]].iloc[range(beg_test,end_test+1)]
    implied_probabilities=1/odds
    p=pd.Series(list(zip(prediction_test_winner,prediction_test_loser,implied_probabilities.PSW,implied_probabilities.PSL)))

    ### For each match in the testing set, if the model predicted the right winner :
    right=(prediction_test_winner>prediction_test_loser).astype(int)
    ### For each match in the testing set, the confidence of the model in the outcome it chose
    def sel_match_confidence(x):
        if x[0]>x[1]:
            return x[0]/x[2] 
        else:
            return x[1]/x[3] 
    confidence=p.apply(lambda x:sel_match_confidence(x))
    
    ### The final confidence dataset
    confidenceTest=pd.DataFrame({"match_index":range(beg_test,end_test+1),
                                 "correct"+model_name:right,
                                 "confidence"+model_name:confidence,
                                 "PSW":odds.PSW.values,
                                 "PSL":odds.PSL.values,
                                 "Confidence_Player1_Wins"+model_name:prediction_test_winner,
                                 "Confidence_Player2_Wins" + model_name: prediction_test_loser})
    confidenceTest=confidenceTest.sort_values("confidence"+model_name,ascending=False).reset_index(drop=True)
    return confidenceTest

def vibratingAssessStrategyGlobal(test_match, dur_train, duration_val_matches, delta, xgb_params, nb_players, nb_tournaments, xtrain, data, weights):
    """
    The ROI is very sensistive to the training set. A few more matches in the training set can 
    change it in a non-negligible way. Therefore it is preferable to run assessStrategyGlobal several times
    with slights changes in the training set lenght, and then combine the predictions.
    This is what this function does.
    More precisely we compute the confidence dataset of 5 models with slightly different training sets.
    For each match, each model has an opinion of the winner, and a confidence is its prediction.
    For each match, the final chosen outcome is the outcome chosen by the most models (majority voting)
    And the final confidence is the average of the confidences of the models that chose this outcome.
    """

    # We define a step variable which will change the training/validation set lengths
    step = 10
    confTest1=assessStrategyGlobal(test_match, dur_train, duration_val_matches, delta, xgb_params, nb_players, nb_tournaments, xtrain, data, weights, "1")
    confTest2=assessStrategyGlobal(test_match, dur_train - step, duration_val_matches + step, delta, xgb_params, nb_players, nb_tournaments, xtrain, data, weights, "2")
    confTest3=assessStrategyGlobal(test_match, dur_train + step, duration_val_matches - step, delta, xgb_params, nb_players, nb_tournaments, xtrain, data, weights, "3")
    confTest4=assessStrategyGlobal(test_match, dur_train - 3 * step, duration_val_matches + 3 * step, delta, xgb_params, nb_players, nb_tournaments, xtrain, data, weights, "4")
    confTest5=assessStrategyGlobal(test_match, dur_train + 3 * step, duration_val_matches - 3 * step, delta, xgb_params, nb_players, nb_tournaments, xtrain, data, weights, "5")
    confTest6=assessStrategyGlobal(test_match, dur_train + 2 * step, duration_val_matches - 2 * step, delta, xgb_params, nb_players, nb_tournaments, xtrain, data, weights, "6")
    confTest7=assessStrategyGlobal(test_match, dur_train - 2 * step, duration_val_matches + 2 * step, delta, xgb_params, nb_players, nb_tournaments, xtrain, data, weights, "7")
    """
    confTest5=confTest1.copy()
    confTest5.columns = ["Confidence_Player1_Wins5", "Confidence_Player2_Wins5", "PSW", "confidence5", "correct5", "match_index"]
    confTest2=confTest1.copy()
    confTest2.columns = ["Confidence_Player1_Wins2", "Confidence_Player2_Wins2", "PSW", "confidence2", "correct2", "match_index"]
    confTest3=confTest1.copy()
    confTest3.columns = ["Confidence_Player1_Wins3", "Confidence_Player2_Wins3", "PSW", "confidence3", "correct3", "match_index"]
    confTest4=confTest1.copy()
    confTest4.columns = ["Confidence_Player1_Wins4", "Confidence_Player2_Wins4", "PSW", "confidence4", "correct4", "match_index"]
    """
    if (type(confTest1)!=int)&(type(confTest2)!=int)&(type(confTest3)!=int)&(type(confTest4)!=int)&(type(confTest5)!=int)&(type(confTest6)!=int)&(type(confTest7)!=int):
        c=confTest1.merge(confTest2,on=["match_index","PSW","PSL"])
        c=c.merge(confTest3,on=["match_index","PSW","PSL"])
        c=c.merge(confTest4,on=["match_index","PSW","PSL"])
        c=c.merge(confTest5,on=["match_index","PSW","PSL"])
        c=c.merge(confTest6,on=["match_index","PSW","PSL"])
        c=c.merge(confTest7,on=["match_index","PSW","PSL"])
        c=pd.Series(list(zip(c.correct1,c.correct2,c.correct3,c.correct4,c.correct5,c.correct6,c.correct7,
                             c.confidence1,c.confidence2,c.confidence3,
                             c.confidence4,c.confidence5,c.confidence6,c.confidence7,c.Confidence_Player1_Wins1,
                             c.Confidence_Player1_Wins2,c.Confidence_Player1_Wins3,
                             c.Confidence_Player1_Wins4,c.Confidence_Player1_Wins5,c.Confidence_Player1_Wins6,c.Confidence_Player1_Wins7,c.Confidence_Player2_Wins1,
                             c.Confidence_Player2_Wins2,c.Confidence_Player2_Wins3,
                             c.Confidence_Player2_Wins4,c.Confidence_Player2_Wins5,c.Confidence_Player2_Wins6,c.Confidence_Player2_Wins7)))
        c=pd.DataFrame.from_records(list(c.apply(mer)))
        conf=pd.concat([confTest1[["match_index","PSW","PSL"]],c],1)
        conf.columns=["match_index","Player1 Odds","Player2 Odds","correct_prediction","confidence","Confidence_Player1_Wins","Confidence_Player2_Wins"]
    else:
        conf=0

    return conf

def mer(t):
    # If more than half the models choose the right outcome for the match, we can say
    # in real situation we would have been right. Otherwise wrong.
    # And the confidence in the chosen outcome is the mean of the confidences of the models
    # we chose this outcome.
    w=np.array([t[0],t[1],t[2],t[3],t[4],t[5],t[6]]).astype(bool)
    conf=np.array([t[7],t[8],t[9],t[10],t[11],t[12],t[13]])
    Conf_P1_Wins=np.array([t[14],t[15],t[16],t[17],t[18],t[19],t[20]])
    Conf_P2_Wins=np.array([t[21],t[22],t[23],t[24],t[25],t[26],t[27]])
    if w.sum()>=4:
        return 1,conf[w].mean(),Conf_P1_Wins[w].mean(),Conf_P2_Wins[w].mean()
    else:
        return 0,conf[~w].mean(),Conf_P1_Wins[~w].mean(),Conf_P2_Wins[~w].mean()

############################### PROFITS COMPUTING ############

def profitComputation(conf_threshold,confidence):
    """
    Input : we bet on the matches with confidence above a certain threshold
    Output : ROI
    """
    final_amount=0
    total_bet=0
    for index, bet in confidence.iterrows():
        if bet["confidence"]>=conf_threshold:
            total_bet+=1
            final_amount+=bet["Pinnacle_Odds"]
    # we compute the ROI which is only the diff between the number of bets and the sums of odds
    # (we assume here a bet of 1 each time)
    return (final_amount-total_bet)/total_bet*100



def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)
