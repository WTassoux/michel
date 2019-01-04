from lxml import html
import lxml
import datetime
import re
from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta, MO

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

"""
sample = open("xpath_file.html","r")

text = sample.read()

tree = html.fromstring(text)


match_score_text_xpath = "//table[contains(@class, 'day-table')]/tbody[2]/tr[6]/td[contains(@class, 'day-table-score')]/a/node()"
match_score_text_parsed = xpath_parse(tree, match_score_text_xpath)
print(match_score_text_parsed)
clean_score=[]

for i in range(0,len(match_score_text_parsed)):
    cleaned=[]
    if isinstance(match_score_text_parsed[i], lxml.etree._ElementStringResult) and match_score_text_parsed[i].strip()!='':
        cleaned=match_score_text_parsed[i].strip().split(' ')
    for j in range(0,len(cleaned)):
        clean_score=clean_score+list(cleaned[j])

print(clean_score)

sample.close()
# data from this url: https://www.atptour.com/en/players/maximilian-marterer/mn13/rankings-history
datafile = open("marterer_ranking_data_page.html","r")
data = sample.read()
datafile.close()
ranking_tree = html.fromstring(data)

"""

# retrieve player historical ranking
# we use a local csv to store all ranking history for all players to avoid multiplying the http calls
# we check in this csv file if data is available otherwise we get it online and append the local db
# the csv contains the following: Player name, Date (always a Monday), Ranking
player_ranking_db=open("player_ranking_data.csv","r")
name="Maximilian Marterer"
date="2010.12.12"

#we have a date and player in input
def getRanking(name,date):
    # we get the previous monday
    current_date=datetime.strptime(date,"%Y.%m.%d")
    previous_monday = current_date + relativedelta(weekday=MO(-1))
    #print("Previous monday was: "+previous_monday.strftime("%Y.%m.%d"))
    partial_row="Maximilian Marterer,"+previous_monday.strftime("%Y.%m.%d")
    ranking=-1
    for row in player_ranking_db:
        if partial_row in row:
            data=row.split(',')
            ranking=data[2]
            break
    #case where we do not have the data in the table, we fetch it online and append it to our csv file
    if ranking==-1:
        # code to fetch the data
        rankingTree = open("marterer_ranking_data_page.html","r")
        text = rankingTree.read()
        atptree = html.fromstring(text)
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
                #we add this result to our local db file
                ranking_db=open("player_ranking_data.csv","a")
                line="\n"+name+","+previous_monday.strftime("%Y.%m.%d")+","+ranking
                ranking_db.write(line)
                ranking_db.close()
                break
    #case where we did not find a match at all
    if ranking==-1:
        ranking = 2000
    return ranking

atp=getRanking(name,date)
print(atp)