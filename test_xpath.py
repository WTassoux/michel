from lxml import html
import lxml
import datetime
import requests
import re
from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta, MO
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# Going headless
#options = Options()
#options.add_argument('--headless')
#options.add_argument('--disable-gpu')  # Last I checked this was necessary.
#driver = webdriver.Chrome('/usr/bin/chromedriver', chrome_options=options)

#from lxml.etree import fromstring

# Python 2 backwards compatibility
try:
    # Python 2
    xrange
except NameError:
    # Python 3, xrange is now named range
    xrange = range

def xpath_parse(tree, xpath):
    result = tree.xpath(xpath)
    return result

def regex_strip_array(array):
    for i in xrange(0, len(array)):
        array[i] = regex_strip_string(array[i]).strip()
    return array

def regex_strip_string(string):
    string = re.sub('\n', '', string).strip()
    string = re.sub('\r', '', string).strip()
    string = re.sub('\t', '', string).strip()
    return string
    
def html_parse_tree(url):
    page=''
    while page == '':
        try:
            page = requests.get(url)
            break
        except:
            print("Connection refused by the server..")
            print("Waiting for 5 seconds before retrying")
            time.sleep(5)
            print("Was a nice sleep, now let me continue...")
        continue
    tree = html.fromstring(page.content)
    return tree




# Retrieve future matches and matches that have not finished yet
tourney_url="https://www.atptour.com/en/scores/current/sydney/338/daily-schedule"
tourney_tree = html_parse_tree(tourney_url)

tourney_days_xpath = "//ul[@data-value='day']/li/@data-value"
days_parsed = xpath_parse(tourney_tree, tourney_days_xpath)

# we loop on the days planned (could be max 2 days)
for z in xrange(0,len(days_parsed)):
    day_url="https://www.atptour.com/en/scores/current/sydney/338/daily-schedule?day="+days_parsed[z]
    day_tree = html_parse_tree(day_url)
    
    date_xpath = "//h3[@class='day-table-date']/text()"
    date_parsed = xpath_parse(day_tree, date_xpath)
    today=datetime.strptime(date_parsed[0],"%A, %B %d, %Y")
    
    # we prepare the data that will be required
    # round
    round_list=regex_strip_array(xpath_parse(day_tree,"//td[@class='day-table-round']/text()"))
    # best of - we use the type of tournament for that
    tourney_type_banner=xpath_parse(day_tree,"//td[@class='tourney-badge-wrapper']/img/@src")
    bestof=3
    if (tourney_type_banner[0].find('slam') != -1): 
        bestof = "5"
    # Player 1
    player1_list=xpath_parse(day_tree,"//td[@class='day-table-name']/a[1]/text()")
    player1url_list=xpath_parse(day_tree,"//td[@class='day-table-name']/a[1]/@href")
    # we reformat the name to remain consistent with historical data
    for h in xrange(0,len(player1_list)):
        first_last_name = player1_list[h].split(' ')
        # we keep only the first letter of first name
        first_name=first_last_name[0].split('-')
            if len(first_name)==2:
                first_last_name[0] = first_name[0][0]+'.'+first_name[1][0]+'.'
            else:
                first_last_name[0] = first_last_name[0][0]+'.'
            # we reconcatenate all the items into one name
            winner_name=''
            for s in xrange(1, len(first_last_name)):
                winner_name=winner_name+first_last_name[s]+' '
            winner_name=winner_name+first_last_name[0]
        player1_list[h]=winner_name
    # Player 2
    player2_list=xpath_parse(day_tree,"//td[@class='day-table-name']/div/a[1]/text()")
    player2url_list=xpath_parse(day_tree,"//td[@class='day-table-name']/div/a[1]/@href")
    # we reformat the name to remain consistent with historical data
    for h in xrange(0,len(player2_list)):
        first_last_name = player2_list[h].split(' ')
        # we keep only the first letter of first name
        first_name=first_last_name[0].split('-')
            if len(first_name)==2:
                first_last_name[0] = first_name[0][0]+'.'+first_name[1][0]+'.'
            else:
                first_last_name[0] = first_last_name[0][0]+'.'
            # we reconcatenate all the items into one name
            winner_name=''
            for s in xrange(1, len(first_last_name)):
                winner_name=winner_name+first_last_name[s]+' '
            winner_name=winner_name+first_last_name[0]
        player2_list[h]=winner_name
    # Match label - to know whether the match happened or not yet
    label_list=xpath_parse(day_tree,"(//td[@class='day-table-vertical-label'])/text()")
    # Round - needs to be converted
    round_list=regex_strip_array(xpath_parse(day_tree,"//td[@class='day-table-round']/text()"))
1st Round
2nd Round
3rd Round
4th Round
Quarterfinals
Semifinals
The Final



    # score will always be null so we return an empty list of length 10
    clean_score=[]
    for p in range(len(clean_score),10):
                    clean_score.append('')
    match_data=[]
    print(label_list)

"""
    # we loop on the lists to build the match_data list
    for n in xrange(0,len(player1_list)):
        # Match type - to know whether it is ATP singles or WTA
        type_list=xpath_parse(day_tree,"(//td[@class='day-table-button'])["+(n+1)+"]/a/text()")
        # Label
        label_list=regex_strip_array(xpath_parse(day_tree,"(//td[@class='day-table-vertical-label'])["+(n+1)+"]/span/text()"))

        if type_list[0]=="H2H" and label_list[0]=="VS":
            # Players' ATP ranking
            winner_atp=getRanking(player1_list[n],today.strftime("%Y.%m.%d"),url_prefix+winner_url.replace('overview','rankings-history'),greedy)
            loser_atp=getRanking(player2_list[n],today.strftime("%Y.%m.%d"),url_prefix+loser_url.replace('overview','rankings-history'),greedy)
            # Let's gather the odds for the match
            odds_found=False        
            # We use the levenshtein distance to measure similarity between names (max 3 characters can be different)
            threshold=4
            win_odds=player1_list[n]
            los_odds=player2_list[n]
            # We try yesterday's odds first
            for a in xrange(0,len(odds_tod)):
            # We try today's odds
            if not(odds_found):
                for a in xrange(0,len(odds_tod)):
                    if levenshtein_distance(odds_tod[a][0],win_odds)<threshold and levenshtein_distance(odds_tod[a][1],los_odds)<threshold:
                        oddsw=odds_tod[a][2]
                        oddsl=odds_tod[a][3]
                        odds_found=True
                        break
                    elif levenshtein_distance(odds_tod[a][1],win_odds)<threshold and levenshtein_distance(odds_tod[a][0],los_odds)<threshold:
                        oddsw=odds_tod[a][3]
                        oddsl=odds_tod[a][2]
                        odds_found=True
                        break
            # We try tomorrow's odds if still no luck
            if not(odds_found):
                for a in xrange(0,len(odds_tom)):
                    if levenshtein_distance(odds_tom[a][0],win_odds)<threshold and levenshtein_distance(odds_tom[a][1],los_odds)<threshold:
                        oddsw=odds_tom[a][2]
                        oddsl=odds_tom[a][3]
                        odds_found=True
                        break
                    elif levenshtein_distance(odds_tom[a][1],win_odds)<threshold and levenshtein_distance(odds_tom[a][0],los_odds)<threshold:
                        oddsw=odds_tom[a][3]
                        oddsl=odds_tom[a][2]
                        odds_found=True
                        break
            if not(odds_found):
                print('Odds not found for match :'+win_odds+' - '+los_odds+' on date: '+today.strftime('%Y.%m.%d'))
                oddsl=''
                oddsw=''
            match_data.append([today.strftime('%m/%d/%Y'), tourney_round_name, bestof, player1_list[n], player2_list[n], winner_atp, loser_atp, '', '']+clean_score+['', '', '', oddsw, oddsl])

print(match_data)
"""
"""
sample = open("xpath_file.html","r")

text = sample.read()

tree = html.fromstring(text)


match_score_text_xpath = "//table[contains(@class, 'day-table')]/tbody[2]/tr[6]/td[contains(@class, 'day-table-score')]/a/node()"
match_score_text_parsed = xpath_parse(tree, match_score_text_xpath)
print(match_score_text_parsed)
clean_score=[]

for i in xrange(0,len(match_score_text_parsed)):
    cleaned=[]
    if isinstance(match_score_text_parsed[i], (lxml.etree._ElementStringResult,lxml.etree._ElementUnicodeResult)) and match_score_text_parsed[i].strip()!='':
        cleaned=match_score_text_parsed[i].strip().split(' ')
    for j in xrange(0,len(cleaned)):
        clean_score=clean_score+list(cleaned[j])
for i in range(len(clean_score),10):
    clean_score.append('')
print(clean_score)

sample.close()

# data from this url: https://www.atptour.com/en/players/maximilian-marterer/mn13/rankings-history
datafile = open("marterer_ranking_data_page.html","r")
data = sample.read()
datafile.close()
ranking_tree = html.fromstring(data)


# retrieve player historical ranking
# we use a local csv to store all ranking history for all players to avoid multiplying the http calls
# we check in this csv file if data is available otherwise we get it online and append the local db
# the csv contains the following: Player name, Date (always a Monday), Ranking
url="http://www.atptour.com/en/players/maximilian-marterer/mn13/rankings-history"
name="Maximilian Marterer"
date="2018.10.12"
greedy=False

#we have a date and player in input
# the greedy mode must be used with caution! For speed purposes, it does not check whether the entry already exists
def getRanking(name,date,url,greedy):
    # we get the previous monday
    current_date=datetime.strptime(date,"%Y.%m.%d")
    previous_monday = current_date + relativedelta(weekday=MO(-1))
    #print("Previous monday was: "+previous_monday.strftime("%Y.%m.%d"))
    partial_row="Maximilian Marterer,"+previous_monday.strftime("%Y.%m.%d")
    ranking='-1'
    player_ranking_db=open("player_ranking_data.csv","r")
    for row in player_ranking_db:
        if partial_row in row:
            data=row.split(',')
            ranking=data[2]
            break
    #case where we do not have the data in the table, we fetch it online and append it to our csv file
    if ranking=='-1':
        # code to fetch the data
        atptree = html_parse_tree(url)
        list_dates_xpath = "//table[contains(@class, 'mega-table')]/tbody/tr/td[1]/text()"
        list_dates_text_parsed = xpath_parse(atptree, list_dates_xpath)
        list_dates=regex_strip_array(list_dates_text_parsed)

        list_rankings_xpath = "//table[contains(@class, 'mega-table')]/tbody/tr/td[2]/text()"
        list_rankings_text_parsed = xpath_parse(atptree, list_rankings_xpath)
        list_rankings=regex_strip_array(list_rankings_text_parsed)
        # we iterate through each date
        for i in xrange(0, len(list_dates)):
            this_monday=datetime.strptime(list_dates[i],"%Y.%m.%d")
            if(this_monday==previous_monday):
                ranking=list_rankings[i]
                #we add this result to our local db file (or all results is greedy mode ON)
                ranking_db=open("player_ranking_data.csv","a")
                if greedy:
                    for j in xrange(0,len(list_rankings)):
                        line="\n"+name+","+list_dates[j]+","+list_rankings[j]
                        ranking_db.write(line)
                else:
                    line="\n"+name+","+list_dates[i]+","+ranking
                    ranking_db.write(line)
                ranking_db.close()
                break
    #case where we did not find a match at all or player did not get atp point yet
    if ranking=='-1' or ranking=='0':
        ranking = '2000'
    # case where player is tied (ranking finished with a T that needs to be removed)
    elif not(ranking.isdigit()):
        ranking=ranking[:-1]
    return ranking

atp=getRanking(name,date,url,greedy)
print(atp)


# data from this url: https://www.oddsportal.com/matches/tennis/20181231/ date format is YYYYMMDD
#datafile = open("odds_portal_html_example.html","r")
#data = datafile.read()
#datafile.close()
#odds_tree = html.fromstring(data)

# we have a date and both players in input
# we do not check whether the match played is in the correct tournament, we assume they can only play in one tourney at once
# We retrieve the whole data to ensure we call the website only once
# Input: the match date
# Output: the list of matches with the player1, player2 and their respective odds
def getDailyOdds(date):
    # each entry is a list with player1, player2, and their respective odds
    #print(date)
    date=date.split('.')
    day=date[0]+date[1]+date[2]
    url='https://www.oddsportal.com/matches/tennis/'+day+'/'
    # let's retrieve the odds for that date
    #print(url)
    odds_tree = html_parse_tree(url)
    print(odds_tree)
    # each entry is a list with player1, player2, and their respective odds
    odds_table=[]

    # let's fetch the loser's name
    match_odds_loser_text_xpath = "//td[contains(@class, 'name table-participant')]/a/text()"
    match_odds_loser_text_parsed = xpath_parse(odds_tree, match_odds_loser_text_xpath)
    # let's fetch the winner's name
    match_odds_winner_text_xpath = "//td[contains(@class, 'name table-participant')]/a/span/text()"
    match_odds_winner_text_parsed = xpath_parse(odds_tree, match_odds_winner_text_xpath)
    # let's fetch the odds
    match_odds_text_xpath = "//a[contains(@xparam, 'odds_text')]/text()"
    match_odds_text_parsed = xpath_parse(odds_tree, match_odds_text_xpath)
    
    # let's clean the results
    n=0
    for i in xrange(0,len(match_odds_loser_text_parsed)):
        cleanup = match_odds_loser_text_parsed[i].split(' - ')
        if cleanup[0]=='':
            odds_table.append([match_odds_winner_text_parsed[n],cleanup[1].strip(),match_odds_text_parsed[2*i],match_odds_text_parsed[2*i+1]])
            n+=1
        elif cleanup[1]=='':
            odds_table.append([match_odds_winner_text_parsed[n],cleanup[0].strip(),match_odds_text_parsed[2*i+1],match_odds_text_parsed[2*i]])
            n+=1
        # case where we have no match in bold and this xpath query returned both winner and loser
        # we need to check the sets to know who won
        else:
            print(cleanup)
            match_sets_text_xpath = "//td[contains(@class, 'center bold table-odds table-score')]/text()"
            match_sets_text_parsed = xpath_parse(odds_tree, match_sets_text_xpath)
            score=match_sets_text_parsed[i].split(':')
            if score[0]>score[1]:
                odds_table.append([cleanup[0].strip(),cleanup[1].strip(),match_odds_text_parsed[2*i],match_odds_text_parsed[2*i+1]])
            else:
                odds_table.append([cleanup[1].strip(),cleanup[0].strip(),match_odds_text_parsed[2*i+1],match_odds_text_parsed[2*i]])



    return odds_table


date = "2019.01.07"

#odds=getDailyOdds(date)

#print(odds)
url = "https://www.oddsportal.com/matches/tennis/20190109/"
browser = webdriver.Chrome('/usr/bin/chromedriver', chrome_options=options)

browser.get(url)
#soup = BeautifulSoup(browser.page_source)
tree = html.fromstring(browser.page_source)

sample = open("xpath_sets_score.html","r")
text = sample.read()
tree = html.fromstring(text)

match_allodds_text_xpath = "//td[contains(@class, 'odds-nowrp')]/@xodd"
match_allodds_text_parsed = xpath_parse(tree, match_allodds_text_xpath)
print(match_allodds_text_parsed)
print(len(match_allodds_text_parsed))

all_match_sets_text_xpath = "//td[contains(@class, 'center bold table-odds table-score') or contains(@class, 'table-score table-odds live-score center bold')]/node()"
all_match_sets_text_parsed = xpath_parse(tree, all_match_sets_text_xpath)
print(all_match_sets_text_parsed)
print(len(all_match_sets_text_parsed))

next_node_xpath = "//td[contains(@class, 'name table-participant')]/following::td[1]/@class"
next_node_parsed = xpath_parse(tree, next_node_xpath)
print(next_node_parsed)
print(len(next_node_parsed))

final_sets_list=[]
h=0
for g in xrange(0,len(next_node_parsed)):
    if next_node_parsed[g]=='odds-nowrp':
        final_sets_list.append('')
    else:
        final_sets_list.append(all_match_sets_text_parsed[h])
        h+=1
print(final_sets_list)


import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

# Compute similarity between player names and tournaments
def levenshtein_distance(a,b):
    # Let's normalize the strings
    # Remove all ponctuation, special characters and accents
    a=a.replace('-',' ')
    b=b.replace('-',' ')
    a=a.replace('.',' ')
    b=b.replace('.',' ')
    a=remove_accents(a)
    b=remove_accents(b)
    a=a.strip()
    b=b.strip()
    a=a.lower()
    b=b.lower()
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n

    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)

    return current[n]

name1="de Minaur A."
name2="De Minaur A."


print(levenshtein_distance(name1,name2))

"""