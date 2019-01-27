from dcm import dataCleaner
import pandas
import numpy
from datetime import *
from dateutil.relativedelta import relativedelta, MO
import math

def g(phi):
    return 1/sqrt(1+3*phi_loser^2/math.pi)
    
def E(mu, muj, phij):
    return 1/(1+exp(-g(phij)*(mu-muj)))


def glickoRanking(df, period, delta_volatility):
    """
    Given the list on matches in chronological order, for each match, computes 
    the glicko ranking of the 2 players at the beginning of the match
    The period is given in days
    The delta_volatility is a constant to constrain the change of volatility over time

    The selected period is 7 days, following the ATP ranking updates, and the update occurs every mondays
    On each pass, all rankings are updated: for player who do not play, their RD increases
    
    """
    print("Glicko-2 rankings computing...")
    players=list(pandas.Series(list(df.Winner)+list(df.Loser)).value_counts().index)
    # For an unrated player, we start with a rating of 1500, a RD of 350 and volatility of 0.06
    # This is the default value for all players
    glickoRK=pandas.Series(numpy.ones(len(players))*1500,index=players)
    glickoRD=pandas.Series(numpy.ones(len(players))*350,index=players)
    glickoSig=pandas.Series(numpy.ones(len(players))*0.06,index=players)
    # we use thie isActive list to know whether the player's ranking needs to be computed
    # if not active, then we leave the ranking as is. This is to avoid players who haven't played yet to have their ranking change from the initial one
    # by default, everyone is inactive
    isActive=pandas.Series(numpy.ones(len(players))*0,index=players)
    
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
            
            
            # If this player played last week, we compute his new score
            lwp=list(pandas.Series(list(lwm.Winner)+list(lwm.Loser)).value_counts().index)
            if player1 is in lwp:
                p1Matches=lwp[lwp.Winner==player1|lwp.Loser==player1]
                r=glickoRK[player1]
                mu=glickoRD[player1]
                nu=0
                wnl=[]
                for j in range(0,len(p1Matches)):
                    mu_winner=(glickoRK[wp.iloc[i,:].Winner]-1500)/173.7178
                    mu_loser=(glickoRK[wp.iloc[i,:].Loser]-1500)/173.7178
                    phi_winner=glicko_winner[1]/173.7178
                    phi_loser=glicko_loser[1]/173.7178
                    if lwp.iloc[i,:].Winner==player1:
                        nu+=(g(phi_loser)^2)*E(mu_winner,mu_loser,phi_loser)*(1-E(mu_winner,mu_loser,phi_loser))
                    else:
                        nu+=(g(phi_winner)^2)*E(mu_loser,mu_winner,phi_winner)*(1-E(mu_loser,mu_winner,phi_winner))
                nu=1/nu
                
            # If this player didn't play last week and isActive is False, we set isActive to True and do not change the score
            
            # If this player didn't play last week and isActive is True, we compute his new score
            
            # For all the other players that did not play this week and whose isActive boolean is True, we compute the new score
            #on parcours la liste complete et on compare si le joueur est dans la liste des matchs de cette semaine
            # increment the week and start again!
        df_this_week=df_this_week+timedelta(weeks=1)
        
    """

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
    """
    return df


df=dataCleaner()

df=glickoRanking(df,7,0.3)

df.to_csv('glicko_output.csv', sep=',', encoding='utf-8',index=False)
