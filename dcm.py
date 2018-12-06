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
from datetime import datetime, timedelta


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
    filenames=list(glob.glob("TestData/20*.xls*"))
    data=[pandas.read_excel(filename) for filename in filenames]

    # Some odds are missing and we need to clean the data
    # Only pinnacle odds are treated as they are deemed the most accurate
    no_pinnacle_odd=[i for i,d in enumerate(data) if "PSW" not in data[i].columns]
    for i in no_pinnacle_odd:
        data[i]["PSW"]=numpy.nan
        data[i]["PSL"]=numpy.nan
    
    #We only keep the following columns: ATP/Location/Tournament/Date/Series/Court/Surface/Round/Bestof/Winner/Loser/WRank/LRank/Wsets/Lsets/Comment/PSW/PSL
    data=[x[list(x.columns)[:13]+["Wsets","Lsets","Comment"]+["PSW","PSL"]] for x in data]
    dataset=pandas.concat(data)
    
    ##########################################
    ### The data needs to be cleaned a bit ###
    ##########################################
    # First, we  sort by date
    dataset=dataset.sort_values("Date")
    
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
    dataset["Lsets"]=dataset["Lsets"].astype(float)
    dataset=dataset.reset_index(drop=True)

    return dataset




def glickoRanking(df, period, delta_volatility):
    """
    Given the list on matches in chronological order, for each match, computes 
    the glicko ranking of the 2 players at the beginning of the match
    The period is given in days
    The delta_volatility is a constant to constrain the change of volatility over time

    The selected period is 7 days, following the ATP ranking updates
    On each pass, all rankings are updated: for player who do not play, their RD increases

    
    """
    print("Glicko-2 rankings computing...")
    players=list(pandas.Series(list(df.Winner)+list(df.Loser)).value_counts().index)
    glicko=pandas.Series(numpy.ones((len(players),3)),index=players)
    # For an unrated player, we start with a rating of 1500, a RD of 350 and volatility of 0.06
    glicko[:,0]*=1500
    glicko[:,1]*=350
    glicko[:,2]*=0.06
    
    glicko_ranking=[(1500,350,0.06),(1500,350,0.06)]
    for i in range(1,len(data)):
        winner=data.iloc[i-1,:].Winner
        loser=data.iloc[i-1,:].Loser
        # We retrieve the current player's rankings
        glicko_winner=glicko[winner]
        glicko_loser=glicko[loser]
        # We convert the rating to the glicko scale
        mu_winner=(glicko_winner[0]-1500)/173.7178
        mu_loser=(glicko_loser[0]-1500)/173.7178
        phi_winner=glicko_winner[1]/173.7178
        phi_loser=glicko_loser[1]/173.7178

        # Sigma remains the same
        sigma_winner=glicko_winner[2]
        sigma_loser=glicko_loser[2]

        # We compute the change in rating now
        variance_winner=1/(g_function(phi_winner)*e_function(mu_winner,mu_loser,phi_loser))
        variance_loser=1/(g_function(phi_loser)*e_function(mu_loser,mu_winner,phi_winner))
        rating_change_winner=variance_winner*g_function(phi_loser)*(1-e_function(mu_winner,mu_loser,phi_loser))
        rating_change_loser=variance_loser*g_function(phi_winner)*(-e_function(mu_loser,mu_winner,phi_winner))
        
        # We now compute the new volatility
        vol_winner=new_sigma_function(sigma_winner, rating_change_winner, phi_winner, variance_winner, delta_volatility, 0.000001)
        vol_loser=new_sigma_function(sigma_loser, rating_change_loser, phi_loser, variance_loser, delta_volatility, 0.000001)
        
        # We update both player's rankings
        glicko[winner]=((glicko_winner+rating_change_winner),variance_winner,vol_winner)
        glicko[loser]=((glicko_loser+rating_change_loser),variance_loser,vol_loser)
        
        # We set the new glicko ranking on the next match of each player
        glicko_ranking.append((glicko[data.iloc[i,:].Winner],glicko[data.iloc[i,:].Loser])) 
        if i%500==0:
            print(str(i)+" matches computed...")
    glicko_ranking=pandas.DataFrame(glicko_ranking,columns=["glicko_winner","glicko_loser"])    
    glicko_ranking["proba_glicko"]=1 / (1 + 10 ** ((ranking_elo["elo_loser"] - ranking_elo["elo_winner"]) / 400))   
    data = pandas.concat([data,ranking_elo],1) 
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



def g_function(a):
    return 1/math.sqrt(1+3*a**2/math.pi)

def e_function(a,b,c):
    return 1/(1+math.exp(-g_function(c)*(a-b)))

def new_sigma_function(sigma, delta, phi, variance, tau, error):
    a=math.log(sigma**2)
    if delta**2 >= (phi**2+variance**2):
        b=math.log(delta**2-phi**2-variance)
    else:
        k=1
        while sigma_convergence_function((a-k*tau), sigma, delta, phi, variance, tau, error):
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
        past_matches=data[(data.Date<match.Date)&(data.Date>=match.Date-timedelta(days=days))]
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
    7 features added by this function:
    1. Days since last match
    2. Was the last match won ?
    3. Ranking of the last player played
    4. Number of sets of last match played
    5. Number of sets won during last match played
    6. Did the player finish the previous match? (did not retire)
    7. Was the player injued in the specified period?
    """
    ##### Match information extraction (according to the outcome)
    player=match.Winner if outcome==1 else match.Loser
    date=match.Date
    ##### Last matches
    wins=past_matches[past_matches.Winner==player]    
    losses=past_matches[past_matches.Loser==player]    
    todo=pandas.concat([wins,losses],0)
    if len(todo)==0:
        return [numpy.nan]*7
    # Days since last match
    dslm=(date-todo.iloc[-1,:].Date).days
    # Was the last match won ?
    wlmw=int(todo.iloc[-1,:].Winner==player)
    # Ranking of the last player played
    rlpp=todo.iloc[-1,:].WRank
    # Number of sets of last match played
    nslmp=todo.iloc[-1,:]['Best of']
    # Number of sets won during last match played
    nswlmp=todo.iloc[-1,:]['Wsets'] if wlmw==1 else todo.iloc[-1,:]['Lsets']
    # Injuries - iitp + injury last match
    if len(losses)!=0:
        ilm=int(losses.iloc[-1,:].Comment=="Completed")
        iitp=1 if (losses.Comment!="Completed").sum()>0 else 0
    else:
        ilm=numpy.nan
        iitp=numpy.nan
    features_recent=[dslm,wlmw,rlpp,nslmp,nswlmp,ilm,iitp]
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
    2. Did the best ranked person win?
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
    best_ranking=min(best_ranking_as_winner,best_ranking_as_loser)
    features_general.append(best_ranking)
    return features_general