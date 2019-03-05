from dcm import dataCleaner
import pandas
import numpy
from datetime import *
from dateutil.relativedelta import relativedelta, MO
import math
from math import sqrt, exp

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
    print(glicko)
    df=pandas.concat([df,glicko],1)
    return df


df=dataCleaner()

df=glickoRanking(df,7,0.5)

df.to_csv('glicko_output.csv', sep=',', encoding='utf-8',index=False)
