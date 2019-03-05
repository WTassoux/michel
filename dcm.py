###################################################################
#
#
#				DATA MANAGEMENT AND COMPUTATION
#
#
###################################################################
#
#	This tool will be:
#		- Gathering new data online
#		- Formatting the data
#		- Computing additional hyper parameters
#		- Maintain a database of the past data
#
import glob
import pandas
import numpy
import math
from datetime import *
from sklearn import preprocessing
from sklearn.preprocessing import OneHotEncoder
from dateutil.relativedelta import relativedelta, MO
from math import sqrt, exp


# We check if more data is available online

# def dataScrapper():

### TODO ###
# Check online for additional data (once a day?/everytime this script is called)
# Append the csv/xls file with collected data of the day if not already imported
# 
# Need to import ALL ATP matches, including challengers to gather more data (esp. for players ranked between 50 and 250)


# We import all gathered data
def dataCleaner():
    #filenames=list(glob.glob("Data/[0-9]^4.xls*"))
    filenames=list(glob.glob("Data/20*.xls*"))
    data=[pandas.read_excel(filename) for filename in filenames]

    # Some odds are missing and we need to clean the data
    # Only pinnacle odds are treated as they are deemed the most accurate
    no_pinnacle_odd=[i for i,d in enumerate(data) if "PSW" not in data[i].columns]
    for i in no_pinnacle_odd:
        data[i]["PSW"]=numpy.nan
        data[i]["PSL"]=numpy.nan
    
    #We only keep the following columns: ATP/Location/Tournament/Date/Series/Court/Surface/Round/Bestof/Winner/Loser/WRank/LRank/Wsets/Lsets/Comment/PSW/PSL
    data=[x[list(x.columns)[:13]+["W1","L1","W2","L2","W3","L3","W4","L4","W5","L5","Wsets","Lsets","Comment"]+["PSW","PSL"]] for x in data]
    dataset=pandas.concat(data)
    
    ##########################################
    ### The data needs to be cleaned a bit ###
    ##########################################
    # First, we  sort by date
    dataset=dataset.sort_values(["Date","Round"],ascending=[True, True],kind='quicksort')
    
    # Some rankings are not provided. In this case we specify Non Ranked people as (NR) as ranked 2000
    dataset["WRank"]=dataset["WRank"].replace("NR",2000)
    dataset["LRank"]=dataset["LRank"].replace("NR",2000)
    # # Some other rankings are displayed as 'N/A' for wildcards and those are removed as it is too hard to predict the outcome of those matches
    dataset=dataset[dataset['WRank'].map(lambda x: math.isnan(x) is False)]
    dataset=dataset[dataset['LRank'].map(lambda x: math.isnan(x) is False)]

    # Now that the rankings are all digits, we force the type to int
    dataset["WRank"]=dataset["WRank"].astype(int)
    dataset["LRank"]=dataset["LRank"].astype(int)
    
    # We convert the Wsets and Lsets data to float as well
    dataset["Wsets"]=dataset["Wsets"].astype(float)
    dataset["Lsets"]=dataset["Lsets"].replace("`1",1)
    dataset["Lsets"]=dataset["Lsets"].astype(float)
    dataset=dataset.reset_index(drop=True)

    return dataset




def glickoRanking(df, period, tau):
    """
    Given the list on matches in chronological order, for each match, computes 
    the glicko ranking of the 2 players at the beginning of the match
    The period is given in days
    The tau is a constant to constrain the change of volatility over time

    The selected period is 7 days, following the ATP ranking updates, and the update occurs every mondays
    On each pass, all rankings are updated: for player who do not play, their RD increases
    
    """
    print("Glicko-2 rankings computing...")
    print("System constant Tau set to: "+str(tau))
    glicko=[]
    players=list(pandas.Series(list(df.Winner)+list(df.Loser)).value_counts().index)
    # For an unrated player, we start with a rating of 1500, a RD of 350 and volatility of 0.06
    # This is the default value for all players
    glickoRK=pandas.Series(numpy.ones(len(players))*1500,index=players)
    glickoRD=pandas.Series(numpy.ones(len(players))*350,index=players)
    glickoSig=pandas.Series(numpy.ones(len(players))*0.06,index=players)
    """
    # Testing data
    print(players)
    glickoRK["a"]=1500
    glickoRK["b"]=1400
    glickoRK["c"]=1550
    glickoRK["d"]=1700
    glickoRD["a"]=200
    glickoRD["b"]=30
    glickoRD["c"]=100
    glickoRD["d"]=300
    print(glickoRK)
    print(glickoRD)
    """
    # we use thie isActive list to know whether the player's ranking needs to be computed
    # if not active, then we leave the ranking as is. This is to avoid players who haven't played yet to have their ranking change from the initial one
    # by default, everyone is inactive
    isActive=pandas.Series(numpy.ones(len(players))*0,index=players)
    alreadyComputed=pandas.Series(numpy.ones(len(players))*0,index=players)
    # we pick the last week of the dataframe to iterate over to know where to stop
    df_last_week=df.iloc[-1,:].Date
    #df_last_week=[df_last_week.isocalendar()[1],df_last_week.isocalendar()[0]]
    # first week setup
    df_this_week=df.iloc[0,:].Date
    df_this_week = df_this_week + relativedelta(weekday=MO(-1))
    #df_this_week=[df_this_week.isocalendar()[1],df_this_week.isocalendar()[0]]
    # we iterate over the weeks and compute the ranking based on the previous' weeks performance
    while df_this_week.isocalendar()[1]<df_last_week.isocalendar()[1]+1 or df_this_week.isocalendar()[0]!=df_last_week.isocalendar()[0]:
        # we get this week's matches
        # First monday of the week is:
        start_week = df_this_week
        end_week = start_week+relativedelta(weeks=1)
        start_last_week=start_week+relativedelta(weeks=-1)
        # This Week Matches are:
        twm=df[(df.Date>=str(start_week))&(df.Date<str(end_week))]
        # Last Week Matches are:
        lwm=df[(df.Date>=str(start_last_week))&(df.Date<str(start_week))]
        
        # Now we iterate on each row in twm and compute the new glicko score based on the previous week's result
        for i in range(0,len(twm)):
            player1=twm.iloc[i,:].Winner
            player2=twm.iloc[i,:].Loser
            #print(twm.iloc[i,:])
            
            # If this player played last week, we compute his new score
            lwp=list(pandas.Series(list(lwm.Winner)+list(lwm.Loser)).value_counts().index)
            if player1 in lwp:
                p1Matches=lwm[(lwm.Winner==player1)|(lwm.Loser==player1)]
                nu=0
                delta=0
                wnl=[]
                for j in range(0,len(p1Matches)):
                    mu_winner=(glickoRK[p1Matches.iloc[j,:].Winner]-1500)/173.7178
                    mu_loser=(glickoRK[p1Matches.iloc[j,:].Loser]-1500)/173.7178
                    phi_winner=glickoRD[p1Matches.iloc[j,:].Winner]/173.7178
                    phi_loser=glickoRD[p1Matches.iloc[j,:].Loser]/173.7178
                    if p1Matches.iloc[j,:].Winner==player1:
                        nu+=(g(phi_loser)**2)*E(mu_winner,mu_loser,phi_loser)*(1-E(mu_winner,mu_loser,phi_loser))
                        delta+=g(phi_loser)*(1-E(mu_winner,mu_loser,phi_loser))
                    elif p1Matches.iloc[j,:].Loser==player1:
                        nu+=(g(phi_winner)**2)*E(mu_loser,mu_winner,phi_winner)*(1-E(mu_loser,mu_winner,phi_winner))
                        delta+=g(phi_winner)*(-E(mu_loser,mu_winner,phi_winner))
                nu=1/nu
                delta=nu*delta
                # We now compute the new volatility
                glickoSig[player1]=new_sigma_function(glickoSig[player1], delta, phi_winner, nu, tau, 0.000001)
                # We update the rating and RD to the new values
                glickoRD[player1]=1/sqrt((1/sqrt(glickoSig[player1]**2+(glickoRD[player1]/173.7178)**2))+(1/nu))
                glickoRK[player1]=(glickoRK[player1]-1500)/173.7178+(glickoRD[player1]**2)*delta/nu
                
                # We convert the values back to the glicko rating
                glickoRD[player1]=glickoRD[player1]*173.7178
                glickoRK[player1]=glickoRK[player1]*173.7178+1500
                alreadyComputed[player1]=True
              
            # If this player didn't play last week and isActive is False, we set isActive to True and do not change the score
            elif not(isActive[player1]):
                isActive[player1]=True
                alreadyComputed[player1]=True
            # If this player didn't play last week and isActive is True, we compute his new score
            # in this case only the RD changes (increases)
            elif not(alreadyComputed[player1]):
                new_phi=glickoRD[player1]/173.7178
                new_phi=sqrt(new_phi**2+glickoSig[player1]**2)
                glickoRD[player1]=new_phi*173.7178

            # we do the same for player 2 now
            if player2 in lwp:
                p2Matches=lwm[(lwm.Winner==player2)|(lwm.Loser==player2)]
                nu=0
                delta=0
                wnl=[]
                for j in range(0,len(p2Matches)):
                    mu_winner=(glickoRK[p2Matches.iloc[j,:].Winner]-1500)/173.7178
                    mu_loser=(glickoRK[p2Matches.iloc[j,:].Loser]-1500)/173.7178
                    phi_winner=glickoRD[p2Matches.iloc[j,:].Winner]/173.7178
                    phi_loser=glickoRD[p2Matches.iloc[j,:].Loser]/173.7178
                    if p2Matches.iloc[j,:].Winner==player2:
                        nu+=(g(phi_loser)**2)*E(mu_winner,mu_loser,phi_loser)*(1-E(mu_winner,mu_loser,phi_loser))
                        delta+=g(phi_loser)*(1-E(mu_winner,mu_loser,phi_loser))
                    elif p2Matches.iloc[j,:].Loser==player2:
                        nu+=(g(phi_winner)**2)*E(mu_loser,mu_winner,phi_winner)*(1-E(mu_loser,mu_winner,phi_winner))
                        delta+=g(phi_winner)*(-E(mu_loser,mu_winner,phi_winner))
                nu=1/nu
                delta=nu*delta
                # We now compute the new volatility
                glickoSig[player2]=new_sigma_function(glickoSig[player2], delta, phi_winner, nu, tau, 0.000001)
                # We update the rating and RD to the new values
                glickoRD[player2]=1/sqrt((1/sqrt(glickoSig[player2]**2+(glickoRD[player2]/173.7178)**2))+(1/nu))
                glickoRK[player2]=(glickoRK[player2]-1500)/173.7178+(glickoRD[player2]**2)*delta/nu
                # We convert the values back to the glicko rating
                glickoRD[player2]=glickoRD[player2]*173.7178
                glickoRK[player2]=glickoRK[player2]*173.7178+1500
                alreadyComputed[player2]=True

            # If this player didn't play last week and isActive is False, we set isActive to True and do not change the score
            elif not(isActive[player2]):
                isActive[player2]=True
                alreadyComputed[player2]=True
            # If this player didn't play last week and isActive is True, we compute his new score
            # in this case only the RD changes (increases)
            elif not(alreadyComputed[player2]):
                new_phi=glickoRD[player2]/173.7178
                new_phi=sqrt(new_phi**2+glickoSig[player2]**2)
                glickoRD[player2]=new_phi*173.7178

            # Now we append the final table with the glicko rankings
            glicko.append((glickoRK[player1],glickoRD[player1],glickoSig[player1],glickoRK[player2],glickoRD[player2],glickoSig[player2]))
            #print(glicko)
        # For all the other players that did not play this week and whose isActive boolean is True, we compute the new score
        twp=list(pandas.Series(list(twm.Winner)+list(twm.Loser)).value_counts().index)
        for n in range(0,len(players)):
            player=players[n]
            if(isActive[player] and (player not in twp)):
                new_phi=glickoRD[player]/173.7178
                new_phi=sqrt(new_phi**2+glickoSig[player]**2)
                glickoRD[player]=new_phi*173.7178

        # increment the week and start again!
        print("Glicko: finished computing week date: "+str(df_this_week))
        # on reset le already computed
        alreadyComputed=pandas.Series(numpy.ones(len(players))*0,index=players)
        df_this_week=df_this_week+timedelta(weeks=1)
    glicko=pandas.DataFrame(glicko,columns=["glickoRK_winner","glickoRD_winner","glickoSig_winner","glickoRK_loser","glickoRD_loser","glickoSig_loser"])
    glicko["proba_glicko"]=1 / (1 + 10 ** ((glicko["glickoRK_loser"] - glicko["glickoRK_winner"]) / 400))  
    #print(glicko)
    df=pandas.concat([df,glicko],1)
    return df


def compute_elo_rankings(data):
    """
    Given the list on matches in chronological order, for each match, computes 
    the elo ranking of the 2 players at the beginning of the match
    
    """
    print("Elo rankings computing...")
    players=list(pandas.Series(list(data.Winner)+list(data.Loser)).value_counts().index)
    elo=pandas.Series(numpy.ones(len(players))*1500,index=players)
    ranking_elo=[(1500,1500)]
    for i in range(1,len(data)):
        w=data.iloc[i-1,:].Winner
        l=data.iloc[i-1,:].Loser
        elow=elo[w]
        elol=elo[l]
        pwin=1 / (1 + 10 ** ((elol - elow) / 400))    
        K_win=32
        K_los=32
        new_elow=elow+K_win*(1-pwin)
        new_elol=elol-K_los*(1-pwin)
        elo[w]=new_elow
        elo[l]=new_elol
        ranking_elo.append((elo[data.iloc[i,:].Winner],elo[data.iloc[i,:].Loser])) 
        if i%500==0:
            print(str(i)+" matches computed...")
    ranking_elo=pandas.DataFrame(ranking_elo,columns=["elo_winner","elo_loser"])    
    ranking_elo["proba_elo"]=1 / (1 + 10 ** ((ranking_elo["elo_loser"] - ranking_elo["elo_winner"]) / 400))  
    data = pandas.concat([data,ranking_elo],1) 
    return data

def compute_elo2_rankings(data):
    """
    Given the list on matches in chronological order, for each match, computes 
    the elo ranking of the 2 players at the beginning of the match
    Takes into account the score
    """
    print("Elo2 rankings computing...")
    players=list(pandas.Series(list(data.Winner)+list(data.Loser)).value_counts().index)
    elo=pandas.Series(numpy.ones(len(players))*1500,index=players)
    ranking_elo=[(1500,1500)]
    for i in range(1,len(data)):
        w=data.iloc[i-1,:].Winner
        l=data.iloc[i-1,:].Loser
        # Let's compute a score parameter to use in the computation
        win_games=numpy.nan_to_num(data.iloc[i-1,:].W1)+numpy.nan_to_num(data.iloc[i-1,:].W2)+numpy.nan_to_num(data.iloc[i-1,:].W3)+numpy.nan_to_num(data.iloc[i-1,:].W4)+numpy.nan_to_num(data.iloc[i-1,:].W5)
        los_games=numpy.nan_to_num(data.iloc[i-1,:].L1)+numpy.nan_to_num(data.iloc[i-1,:].L2)+numpy.nan_to_num(data.iloc[i-1,:].L3)+numpy.nan_to_num(data.iloc[i-1,:].L4)+numpy.nan_to_num(data.iloc[i-1,:].L5)
        if win_games+los_games != 0:
            #ratio=exp((win_games-los_games)/(win_games+los_games))
            # we use the fermi function to compute the ratio
            x=(win_games-los_games)/(win_games+los_games)
            ratio=1.48*2.5/(1+exp((0.25-x)/0.17))
        else: ratio=1.48
        elow=elo[w]
        elol=elo[l]
        pwin=1 / (1 + 10 ** ((elol - elow) / 400))   
        K_win=25*ratio
        K_los=25*ratio
        new_elow=elow+K_win*(1-pwin)
        new_elol=elol-K_los*(1-pwin)
        elo[w]=new_elow
        elo[l]=new_elol
        ranking_elo.append((elo[data.iloc[i,:].Winner],elo[data.iloc[i,:].Loser])) 
        if i%500==0:
            print(str(i)+" matches computed...")
    ranking_elo=pandas.DataFrame(ranking_elo,columns=["elo_winner","elo_loser"])    
    ranking_elo["proba_elo"]=1 / (1 + 10 ** ((ranking_elo["elo_loser"] - ranking_elo["elo_winner"]) / 400))  
    data = pandas.concat([data,ranking_elo],1) 
    return data



def g(phi):
    return 1/sqrt(1+3*phi**2/math.pi**2)
    
def E(mu, muj, phij):
    return 1/(1+exp(-g(phij)*(mu-muj)))


def new_sigma_function(sigma, delta, phi, variance, tau, error):
    a=math.log(sigma**2)
    if delta**2 >= (phi**2+variance):
        b=math.log(delta**2-phi**2-variance)
    else:
        k=1
        while sigma_convergence_function((a-k*tau), sigma, delta, phi, variance, tau, error)<0:
            #print(sigma_convergence_function((a-k*tau), sigma, delta, phi, variance, tau, error))
            k=k+1
        b=a-k*tau
    fa=sigma_convergence_function(a, sigma, delta, phi, variance, tau, error)
    fb=sigma_convergence_function(b, sigma, delta, phi, variance, tau, error)
    while math.fabs(b-a)>error:
        c=a+(a-b)*fa/(fb-fa)
        fc=sigma_convergence_function(c, sigma, delta, phi, variance, tau, error)
        if fc*fb<0:
            a=b
            fa=fb
        else:
            fa=fa/2
        b=c
        fb=fc
    return math.exp(a/2)

def sigma_convergence_function(x, sigma, delta, phi, variance, tau, error):
    a=math.log(sigma**2)
    return ((math.exp(x)*(delta**2-phi**2-variance-math.exp(x)))/(2*(phi**2+variance+math.exp(x))**2)-(x-a)/tau**2)


def features_past_generation(features_creation_function,
                             days,
                             feature_names_prefix,
                             data,
                             indices):
    """
    Creates features based on the past of the players. 
    Basically a for loop. Takes 1 match at a time, selects the matches that occurred during 
    its close past (usually 150 days before max) and computes some features.
    Each match will appear twice in the dataset : 1 time per outcome of the match.
    Example : 02/03/2016 Djoko-Zverev ,Djoko won
        During the 150 days before the match, Djoko won 80% of its matches and Zverev 40%.
        We encode the outcome "Djoko wins" like that : [80,40], and tell the model this outcome happened (1).
        We encode the outcome "Zverev wins" like that : [40,80], and tell the model it didn't happen (0).
    And we do that with some more features , based on the players past stats on the surface
    of the match, on the recent injuries, ...
    In the inputs of the function, "indices" contains the indices of the matches we want to encode.
    The output of the functions is twice as long as "indices".
    (these features introduce many hyperparameters to be tuned...)
    """
    matches_outcomes=[]
    for i,match_indice in enumerate(indices):
        match=data.iloc[match_indice,:]
        matchDate=datetime.strptime(match.Date, '%Y-%m-%d').date()
        past_matches=data[(data.Date<match.Date)&(data.Date>=str(matchDate-timedelta(days=days)))]
        match_features_outcome_1=features_creation_function(1,match,past_matches)
        match_features_outcome_2=features_creation_function(2,match,past_matches)
        matches_outcomes.append(match_features_outcome_1)
        matches_outcomes.append(match_features_outcome_2)
        if i%500==0:
            print(str(i)+"/"+str(len(indices))+" matches treated.")
    train=pandas.DataFrame(matches_outcomes)
    train.columns=[feature_names_prefix+str(i) for i in range(len(train.columns))]
    return train


def features_player_creation(outcome,match,past_matches):
    features_player=[]
    """
    8 features added by this function:
    1. Number of matches won
    2. Number of matches lost
    3. Total number of matches played
    4. Percentage of matches won
    5. Number of matches won on that surface
    6. Number of matches lost on that surface
    7. Total number of matches played on that surface
    8. Percentage of matches won on that surface
    """
    ##### Match information extraction (according to the outcome)
    player=match.Winner if outcome==1 else match.Loser
    surface=match.Surface
    ##### General stats
    wins=past_matches[past_matches.Winner==player]    
    losses=past_matches[past_matches.Loser==player]    
    todo=pandas.concat([wins,losses],0)
    features_player+=[len(wins),len(losses),len(todo)]
    per_victory=100*len(wins)/len(todo) if len(todo)>0 else numpy.nan
    features_player.append(per_victory)
    ##### Surface
    past_surface=past_matches[past_matches.Surface==surface]
    wins_surface=past_surface[past_surface.Winner==player]    
    losses_surface=past_surface[past_surface.Loser==player]    
    todo_surface=pandas.concat([wins_surface,losses_surface],0)
    features_player+=[len(wins_surface),len(losses_surface),len(todo_surface)]
    per_victory_surface=100*len(wins_surface)/len(todo_surface) if len(todo_surface)>0 else numpy.nan
    features_player.append(per_victory_surface)
    return features_player

def features_recent_creation(outcome,match,past_matches):
    """
    8 features added by this function:
    1. Days since last match
    2. Was the last match won ?
    3. Ranking of the last player played
    4. Number of sets of last match played - feature removed
    5. Number of sets won during last match played - feature removed
    6. Did the player finish the previous match? (did not retire)
    7. Was the player injured in the specified period?
    8. Fatigue score which is the number of games played in the past 3 days with weighted by the factor 0.75 to the power the number of day
    """
    ##### Match information extraction (according to the outcome)
    player=match.Winner if outcome==1 else match.Loser
    date=match.Date
    ##### Last matches
    #wins=past_matches[past_matches.Winner==player]    
    losses=past_matches[past_matches.Loser==player]    
    #todo=pandas.concat([wins,losses],0)
    todo=past_matches[(past_matches.Loser==player)|(past_matches.Winner==player)] 
    if len(todo)==0:
        return [numpy.nan]*7
    # Days since last match
    dslm=(datetime.strptime(date, '%Y-%m-%d').date()-datetime.strptime(todo.iloc[-1,:].Date, '%Y-%m-%d').date()).days
    # Was the last match won ?
    wlmw=int(todo.iloc[-1,:].Winner==player)
    # Ranking of the last player played
    if wlmw:
        rlpp=todo.iloc[-1,:].LRank
    else:
        rlpp=todo.iloc[-1,:].WRank
    # Number of sets of last match played
    nslmp=todo.iloc[-1,:]['Wsets']+todo.iloc[-1,:]['Lsets']
    # Number of sets won during last match played
    nswlmp=todo.iloc[-1,:]['Wsets'] if wlmw==1 else todo.iloc[-1,:]['Lsets']
    # Injuries - iitp + injury last match
    if len(losses)!=0:
        ilm=int(losses.iloc[-1,:].Comment=="Completed")
        iitp=1 if (losses.Comment!="Completed").sum()>0 else 0
    else:
        ilm=numpy.nan
        iitp=numpy.nan
    # Fatigue score
    # list of all matches played in the last 3 days
    fs=0
    SevenDaysAgo=datetime.strptime(date, '%Y-%m-%d').date()-timedelta(days=3)
    fatigueMatches=todo[todo.Date>=str(SevenDaysAgo)]
    for index, match in fatigueMatches.iterrows():
        day=(datetime.strptime(date, '%Y-%m-%d').date()-datetime.strptime(match["Date"], '%Y-%m-%d').date()).days
        coeff=pow(0.75,day-1)
        fs+=match[13:23].sum(skipna=True)*coeff
        #fs+=match["W1"]+match["L1"]+match["W2"]+match["L2"]+match["W3"]+match["L3"]+match["W4"]+match["L4"]+match["W5"]+match["L5"]
    #print(fs)
    #features_recent=[dslm,wlmw,rlpp,nslmp,nswlmp,ilm,iitp,fs]
    features_recent=[dslm,wlmw,rlpp,ilm,iitp,fs]
    return features_recent

def features_h2h_creation(outcome,match,past):
    """
    4 features added by this function:
    1. Total number of matches played between these 2 players in the past period
    2. Number of matches won
    3. Number of matches lost
    4. Percentage of won matches in the H2H
    """
    features_h2h=[]
    ##### Match information extraction (according to the outcome)
    player1=match.Winner if outcome==1 else match.Loser
    player2=match.Loser if outcome==1 else match.Winner
    ##### General h2h features
    # % of the previous matches between these 2 players won by each.
    h2h1=past[(past.Winner==player1)&(past.Loser==player2)]    
    h2h2=past[(past.Winner==player2)&(past.Loser==player1)]    
    h2h=pandas.concat([h2h1,h2h2],0)
    features_h2h+=[len(h2h),len(h2h1),len(h2h2)]
    per_victory_player1=100*len(h2h1)/len(h2h) if len(h2h)>0 else numpy.nan
    features_h2h.append(per_victory_player1)
    return features_h2h

def features_general_creation(outcome,match,past_matches):
    """
    3 features added by this function:
    1. Difference in ATP rank between the winner and the loser
    2. Did the best ranked person win? (1 for no, 0 for yes
    3. Best player ranking
    """
    features_general=[]
    ##### Match information extraction (according to the outcome)
    player1=match.Winner if outcome==1 else match.Loser
        
    rank_player_1=match.WRank if outcome==1 else match.LRank
    rank_player_2=match.LRank if outcome==1 else match.WRank
    
    features_general+=[rank_player_2-rank_player_1,
                       int(rank_player_1>rank_player_2)]

    best_ranking_as_winner=past_matches[(past_matches.Winner==player1)].WRank.min()
    best_ranking_as_loser=past_matches[(past_matches.Loser==player1)].LRank.min()
    if numpy.isnan(best_ranking_as_winner):
        best_ranking_as_winner=2500
    if numpy.isnan(best_ranking_as_loser):
        best_ranking_as_loser=2500
    #print(best_ranking_as_winner)
    #print(best_ranking_as_loser)
    #print(rank_player_1)
    best_ranking=min(best_ranking_as_winner,best_ranking_as_loser,rank_player_1)
    features_general.append(best_ranking)
    return features_general


def categorical_features_encoding(cat_features):
    """
    Categorical features encoding.
    Simple one-hot encoding.
    """
    cat_features=cat_features.apply(preprocessing.LabelEncoder().fit_transform)
    ohe=OneHotEncoder()
    cat_features=ohe.fit_transform(cat_features)
    cat_features=pandas.DataFrame(cat_features.todense())
    cat_features.columns=["cat_feature_"+str(i) for i in range(len(cat_features.columns))]
    cat_features=cat_features.astype(int)
    return cat_features

def features_players_encoding(data):
    """
    Encoding of the players . 
    The players are not encoded like the other categorical features because for each
    match we encode both players at the same time (we put a 1 in each row corresponding 
    to the players playing the match for each match).
    """
    winners=data.Winner
    losers=data.Loser
    le = preprocessing.LabelEncoder()
    le.fit(list(winners)+list(losers))
    winners=le.transform(winners)
    losers=le.transform(losers)
    encod=numpy.zeros([len(winners),len(le.classes_)])
    for i in range(len(winners)):
        encod[i,winners[i]]+=1
    for i in range(len(losers)):
        encod[i,losers[i]]+=1
    columns=["player_"+el for el in le.classes_]
    players_encoded=pandas.DataFrame(encod,columns=columns)
    return players_encoded

def features_tournaments_encoding(data):
    """
    Encoding of the tournaments . 
    """
    tournaments=data.Tournament
    le = preprocessing.LabelEncoder()
    tournaments=le.fit_transform(tournaments)
    encod=numpy.zeros([len(tournaments),len(le.classes_)])
    for i in range(len(tournaments)):
        encod[i,tournaments[i]]+=1
    columns=["tournament_"+el for el in le.classes_]
    tournaments_encoded=pandas.DataFrame(encod,columns=columns)
    return tournaments_encoded
