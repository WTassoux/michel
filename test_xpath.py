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
import unicodedata
# Python 2 backwards compatibility
try:
    # Python 2
    xrange
except NameError:
    # Python 3, xrange is now named range
    xrange = range


### This web scraper will retrieve future matches and live results from the ATP World Tour website

## We define a few functions first

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

# we convert the round of 16, 32 etc... to 1st, 2nd etc... rounds
# this function works for both syntaxes (current plays and past matches
# we use the levenshtein distance as syntax may change
def convertRound(depth,size):
    #we avoid qualifying rounds
    if "ualifying" in depth:
        return depth
    depth_list=["1st Round","2nd Round","3rd Round","4th Round","Quarterfinals","Semifinals","The Final"]
    real_depth=1
    while 2**real_depth<size:
        real_depth+=1
    real_size=2**real_depth
    if levenshtein_distance(depth,depth_list[-1])<=4 or depth=='F':
        return depth_list[-1]
    if levenshtein_distance(depth,depth_list[-2])<=2 or depth=='SF':
        return depth_list[-2]
    if levenshtein_distance(depth,depth_list[-3])<=2 or depth=='QF':
        return depth_list[-3]
    depth_num=depth[-2:]
    i=real_depth/int(depth_num)
    return depth_list[int(i)]
            

def array2csv(array, filename):
    csv_array = array
    csv_out = open(filename + ".csv", 'w')
    mywriter = csv.writer(csv_out)
    for row in csv_array:
        mywriter.writerow(row)
    csv_out.close()

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
    
    
    
    
url='https://www.oddsportal.com/matches/tennis/20190110/'
# let's retrieve the odds for that date
# this website uses AJAX calls after the page loads. Need to use the heavy artillery
# Going headless
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')  # Last I checked this was necessary.
browser = webdriver.Chrome('/usr/bin/chromedriver', chrome_options=options)
browser.get(url)
odds_tree = html.fromstring(browser.page_source)

# each entry is a list with player1, player2, and their respective odds
odds_table=[]
# let's fetch the loser's name
match_odds_loser_text_xpath = "//td[contains(@class, 'name table-participant')]/a/text()"
match_odds_loser_text_parsed = xpath_parse(odds_tree, match_odds_loser_text_xpath)
# let's fetch the winner's name
match_odds_winner_text_xpath = "//td[contains(@class, 'name table-participant')]/a/span/text()"
match_odds_winner_text_parsed = xpath_parse(odds_tree, match_odds_winner_text_xpath)
# let's fetch the odds
match_odds_text_xpath = "//td[contains(@class, 'odds-nowrp')]/@xodd"
match_odds_text_parsed = xpath_parse(odds_tree, match_odds_text_xpath)

match_sets_text_xpath = "//td[contains(@class, 'center bold table-odds table-score') or contains(@class, 'table-score table-odds live-score center bold')]/node()"
match_sets_text_parsed = xpath_parse(odds_tree, match_sets_text_xpath)
next_node_xpath = "//td[contains(@class, 'name table-participant')]/following::td[1]/@class"
next_node_parsed = xpath_parse(odds_tree, next_node_xpath)
final_sets_list=[]
h=0
for g in xrange(0,len(next_node_parsed)):
    if next_node_parsed[g]=='odds-nowrp':
        final_sets_list.append('')
    else:
        final_sets_list.append(match_sets_text_parsed[h])
        h+=1
# let's clean the results
n=0
print(final_sets_list)
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
    if len(cleanup)<2:
        if isinstance(final_sets_list[i], lxml.html.HtmlElement):
            score=[]
        else:
            score=final_sets_list[i].split(':')
        if len(score)!=2:
            odds_table.append([cleanup[0].strip(),cleanup[1].strip(),match_odds_text_parsed[2*i],match_odds_text_parsed[2*i+1]])
        elif score[0]>score[1]:
            odds_table.append([cleanup[0].strip(),cleanup[1].strip(),match_odds_text_parsed[2*i],match_odds_text_parsed[2*i+1]])
        else:
            odds_table.append([cleanup[1].strip(),cleanup[0].strip(),match_odds_text_parsed[2*i+1],match_odds_text_parsed[2*i]])

print(odds_table)
