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
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')  # Last I checked this was necessary.
driver = webdriver.Chrome('/usr/bin/chromedriver', chrome_options=options)

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
"""


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


date = "2018.12.29"

#odds=getDailyOdds(date)

#print(odds)

url = "https://www.oddsportal.com/matches/tennis/20181229/"
browser = webdriver.Chrome('/usr/bin/chromedriver', chrome_options=options)

browser.get(url)
#soup = BeautifulSoup(browser.page_source)
tree = html.fromstring(browser.page_source)
match_odds_text_xpath = "//a[contains(@xparam, 'odds_text')]/text()"
match_odds_text_parsed = xpath_parse(tree, match_odds_text_xpath)
print(match_odds_text_parsed)
print(len(match_odds_text_parsed))

match_nodds_text_xpath = "//td[contains(@class, 'odds-nowrp deactivateOdd')]/span/text()"
match_nodds_text_parsed = xpath_parse(tree, match_nodds_text_xpath)
print(match_nodds_text_parsed)


match_allodds_text_xpath = "//td[contains(@class, 'odds-nowrp')]/@xodd"
match_allodds_text_parsed = xpath_parse(tree, match_allodds_text_xpath)
print(match_allodds_text_parsed)
print(len(match_allodds_text_parsed))
