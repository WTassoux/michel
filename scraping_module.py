from lxml import html
import lxml
import requests
import re
import json
import csv
from xlsxwriter.workbook import Workbook
import sys
import time
from datetime import timedelta, datetime, date
import numbers
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures
from dateutil.relativedelta import relativedelta, MO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import unicodedata

greedy=False

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
    
    
# We need the odds for each match. We use oddsportal to get it. It works only 30 days in the past
# for the moment, no module can retrieve the historical odds and those are available at www.tennis-data.co.uk/data.php
#
#https://www.oddsportal.com/matches/tennis/20181231/
#
# we have a date and both players in input
# we do not check whether the match played is in the correct tournament, we assume they can only play in one tourney at once
# We retrieve the whole data to ensure we call the website only once
# Input: the match date YYYY.MM.DD
# Output: the list of matches with the player1, player2 and their respective odds
def getDailyOdds(date):
    #print(date)
    date=date.split('.')
    day=date[0]+date[1]+date[2]
    #print(day)
    url='https://www.oddsportal.com/matches/tennis/'+day+'/'
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
    # we clean the result as we retrieve noise from the webpage
    match_odds_loser_text_parsed = [x for x in match_odds_loser_text_parsed if x != u'\xa0']
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


    return odds_table


def scrape_year(year,start_scraping_date,end_scraping_date):
    # Setup
    year_url = "http://www.atpworldtour.com/en/scores/results-archive?year=" + year
    url_prefix = "http://www.atpworldtour.com"

    # HTML tree
    year_tree = html_parse_tree(year_url)

    # XPaths
    tourney_title_xpath = "//span[contains(@class, 'tourney-title')]/text()"
    tourney_title_parsed = xpath_parse(year_tree, tourney_title_xpath)
    tourney_title_cleaned = regex_strip_array(tourney_title_parsed)
    tourney_count = len(tourney_title_cleaned)
    # Iterate over each tournament
    output = []
    tourney_data = []
    tourney_urls = []
    problem_tourneys = []
    for i in xrange(0, tourney_count):
        tourney_order = i + 1
        tourney_name = tourney_title_cleaned[i]
        
        # We first check that the tournament dates are within the scraping window
        tourney_startdate_url_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[3]/span[contains(@class, 'tourney-dates')]/text()"
        tourney_startdate_url_parsed = xpath_parse(year_tree, tourney_startdate_url_xpath)
        tourney_startdate_url_parsed=tourney_startdate_url_parsed[0].strip()
        tourney_startdate=datetime.strptime(tourney_startdate_url_parsed, '%Y.%m.%d')
        # We assume a tournament can only be 15 days in length so we see if we are in the startdate + 15 window
        tourney_enddate=tourney_startdate+timedelta(days=15)
        # the official startdate does not take into account the qualifying rounds which are usually 2-3 days before
        tourney_startdate=tourney_startdate+timedelta(days=-3)
        if(tourney_enddate<start_scraping_date or tourney_startdate>end_scraping_date):
            continue
        
        # Assign variables
        tourney_details_url_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[8]/a/@href"
        tourney_details_url_parsed = xpath_parse(year_tree, tourney_details_url_xpath)
        #print(tourney_details_url_parsed)

        tourney_location_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[3]/span[contains(@class, 'tourney-location')]/text()"
        tourney_location =xpath_parse(year_tree, tourney_location_xpath)
        tourney_location=tourney_location[0].strip()
        # We keep only the city name and drop the country
        tourney_location=tourney_location.split(',')
        tourney_location=tourney_location[0]
        #print(tourney_location)
        tourney_court_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[5]/div/div[contains(@class, 'item-details')]/text()"
        tourney_court_raw = xpath_parse(year_tree, tourney_court_xpath) 
        tourney_surface_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[5]/div/div/span[contains(@class, 'item-value')]/text()"
        tourney_surface_raw = xpath_parse(year_tree, tourney_surface_xpath)
        tourney_surface =  tourney_surface_raw[0].strip()
        tourney_court = tourney_court_raw[0].strip()
        #print(tourney_surface)
        tourney_class_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td/img/@src"
        tourney_class_raw = xpath_parse(year_tree, tourney_class_xpath)
        tourney_class_raw=tourney_class_raw[0]
        tourney_class = "Unknown"
        if (tourney_class_raw.find('250') != -1): 
            tourney_class = "ATP250" 
        elif (tourney_class_raw.find('500') != -1): 
            tourney_class = "ATP500"
        elif (tourney_class_raw.find('1000') != -1): 
            tourney_class = "Masters 1000"
        elif (tourney_class_raw.find('slam') != -1): 
            tourney_class = "Grand Slam"
        elif (tourney_class_raw.find('finals') != -1): 
            tourney_class = "ATP Finals"
        
        if len(tourney_details_url_parsed) > 0:
            tourney_url_suffix = tourney_details_url_parsed[0]
            tourney_url_split = tourney_url_suffix.split('/')
            tourney_slug = tourney_url_split[4]
            tourney_id = tourney_url_split[5]
            tourney_year_id = str(year) + '-' + tourney_id
            tourney_urls.append(tourney_url_suffix)
        else:
            tourney_url_suffix = ''
            tourney_slug = ''
            tourney_id = ''
            tourney_year_id = ''
            tourney_urls.append(tourney_url_suffix)
            problem_tourneys.append([year, tourney_order, tourney_name])
        
        # Store data        
        tourney_data.append([tourney_order, tourney_location, tourney_name, tourney_class, tourney_court, tourney_surface])

    # Print missing info
    if len(problem_tourneys) > 0:
        print('')
        print('Tournaments with missing match info...')
        print('Year    Order    Tournament')
        print('----    -----    ----------')

        for tourney in problem_tourneys:
            year = tourney[0]
            tourney_order = tourney[1]
            tourney_name = tourney[2]

            spacing_count = 5 - len(str(tourney_order))
            spacing = ''
            for j in xrange(0, spacing_count):
                spacing += ' '

            print(str(year) + '    ' + str(tourney_order) + str(spacing) +  '    ' + str(tourney_name))    

    # Output data
    output = [tourney_data, tourney_urls]
    return output

def scrape_tourney(tourney_url_suffix,start_scraping_date,end_scraping_date):
    url_prefix = "http://www.atpworldtour.com"
    tourney_url = url_prefix + tourney_url_suffix

    url_split = tourney_url.split("/")
    tourney_slug = url_split[6]
    tourney_year = url_split[8]
    tourney_id = url_split[7]

    # Tourney tree
    tourney_tree = html_parse_tree(tourney_url)     
    match_urls = []
    match_data = []
    
    # We retrieve the start date
    tourney_dates_xpath = "//span[contains(@class,'tourney-dates')]/text()"
    tourney_dates = xpath_parse(tourney_tree, tourney_dates_xpath)
    tourney_dates=tourney_dates[0].strip()
    tourney_end_date=datetime.strptime(tourney_dates[13:23], '%Y.%m.%d')
    
    # We figure out the dates of the tournament and try to retrieve the matches for each day
    # This only works for the current year. Past years do not have dates and the iteration needs to be through the rounds directly
    tourney_dates_xpath = "//ul[@data-value='matchdate']/li[@data-value]/text()"
    day_count_parsed = xpath_parse(tourney_tree, tourney_dates_xpath)
    day_match_count = len(day_count_parsed)

    # we see if there is a need to scrap the planned matches as well
    # the scraping will occur at the end of this function
    # even if the date stops at today, we still retrieve the planned matches as some matches may not be finished yet in some timezones
    retrieve_planned_matches=False
    last_parsed_day=datetime.strptime(day_count_parsed[0], '%Y.%m.%d')
    if last_parsed_day<=end_scraping_date:
        retrieve_planned_matches=True

    # check for the case were there are no dates available
    if(day_match_count==0):
        day_match_count=1
    #print(day_match_count)
    # Iterate through each day of the tournament
    for z in xrange(0, day_match_count):
        no_days=False
        if(len(day_count_parsed)!=0):
            tourney_day_tree = html_parse_tree(tourney_url+"?matchdate="+day_count_parsed[z].replace(".","/"))
            today=datetime.strptime(day_count_parsed[z], '%Y.%m.%d')
        else:
            tourney_day_tree = html_parse_tree(tourney_url)
            no_days=True
        
        # Tournament size - required for round computation
        size_list=xpath_parse(tourney_day_tree,"//tr/td/div/div/a/span/text()")
        tourney_size=int(regex_strip_string(size_list[0]))
                
        tourney_round_name_xpath = "//table[contains(@class, 'day-table')]/thead/tr/th/text()"
        tourney_round_name_parsed = xpath_parse(tourney_day_tree, tourney_round_name_xpath)
        tourney_round_count = len(tourney_round_name_parsed)
        #print(tourney_round_name_parsed)
        # Iterate through each round (usually there will only be one round per day  
        # Except in the case were there are no dates available, then we "invent" our own dates 
        for i in xrange(0, tourney_round_count):
            if(no_days):
                today=tourney_end_date+timedelta(days=-i)
            # We check that we are in the scraping window
            if(today<start_scraping_date or today>end_scraping_date):
                continue

            # Odds trees (we gather yesterday, the current day and tomorrow to ensure full coverage with the timezones
            # We assume here we gather dates that can be retrieved (i.e. within 30 days of the present) - so we will have the correct date for sure
            yesterday = today+timedelta(days=-1)
            tomorrow = today+timedelta(days=+1)
            odds_yes = getDailyOdds(yesterday.strftime('%Y.%m.%d'))
            odds_tod = getDailyOdds(today.strftime('%Y.%m.%d'))
            odds_tom = getDailyOdds(tomorrow.strftime('%Y.%m.%d'))

            round_order = i + 1

            tourney_round_name = tourney_round_name_parsed[i]
            tourney_round_name=convertRound(tourney_round_name,tourney_size)
            round_match_count_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr/td[contains(@class, 'day-table-name')][1]/a/text()"
            round_match_count_parsed = xpath_parse(tourney_day_tree, round_match_count_xpath)
            round_match_count = len(round_match_count_parsed)
            #print(round_match_count_parsed)
            # Iterate through each match
            for j in xrange(0, round_match_count):
                match_order = j + 1

                # Winner
                winner_name_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-name')][1]/a/text()"
                winner_name_parsed = xpath_parse(tourney_day_tree, winner_name_xpath)

                winner_url_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-name')][1]/a/@href"
                winner_url_parsed = xpath_parse(tourney_day_tree, winner_url_xpath)

                winner_name = winner_name_parsed[0]
                # we reformat the name to remain consistent with historical data
                first_last_name = winner_name.split(' ')
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
                winner_url = winner_url_parsed[0]
                #winner_url_split = winner_url.split('/')
                #winner_slug = winner_url_split[3]
                #winner_player_id = winner_url_split[4]            

                # Loser
                loser_name_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-name')][2]/a/text()"
                loser_name_parsed = xpath_parse(tourney_day_tree, loser_name_xpath)

                loser_url_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i +1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-name')][2]/a/@href"
                loser_url_parsed = xpath_parse(tourney_day_tree, loser_url_xpath)

                try:
                    loser_name = loser_name_parsed[0]
                    loser_url = loser_url_parsed[0]
                    # we reformat the name to remain consistent with historical data
                    first_last_name = loser_name.split(' ')
                    # we keep only the first letter of first name
                    first_name=first_last_name[0].split('-')
                    if len(first_name)==2:
                        first_last_name[0] = first_name[0][0]+'.'+first_name[1][0]+'.'
                    else:
                        first_last_name[0] = first_last_name[0][0]+'.'
                    # we reconcatenate all the items into one name
                    loser_name=''
                    for s in xrange(1, len(first_last_name)):
                        loser_name=loser_name+first_last_name[s]+' '
                    loser_name=loser_name+first_last_name[0]
                    #loser_url_split = loser_url.split('/')
                    #loser_slug = loser_url_split[3]
                    #loser_player_id = loser_url_split[4]
                # this exeption needs to be handled somehow - not sure when this happens
                except Exception:
                    print("No loser found on "+today.strftime('%Y.%m.%d')+" for winner: "+winner_name)
                    loser_name = ''
                    loser_url = ''
                    #loser_slug = ''
                    #loser_player_id = ''
                
                # Players' ATP ranking
                winner_atp=getRanking(winner_name,today.strftime("%Y.%m.%d"),url_prefix+winner_url.replace('overview','rankings-history'),greedy)
                loser_atp=getRanking(loser_name,today.strftime("%Y.%m.%d"),url_prefix+loser_url.replace('overview','rankings-history'),greedy)
                
                # Match score
                match_score_text_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-score')]/a/node()"
                match_score_text_parsed = xpath_parse(tourney_day_tree, match_score_text_xpath)
                outcome='Completed'
                clean_score=[]
                for c in xrange(0,len(match_score_text_parsed)):
                    cleaned=[]
                    if isinstance(match_score_text_parsed[c], (lxml.etree._ElementStringResult,lxml.etree._ElementUnicodeResult)) and match_score_text_parsed[c].strip()!='':
                        cleaned=match_score_text_parsed[c].strip().split(' ')
                    if cleaned!=[]:
                        if cleaned[0]=='(W/O)':
                            outcome='Walkover' 
                            cleaned=[]
                        elif cleaned[-1]=='(RET)':
                            outcome='Retired'
                            cleaned[-1]=''
                    for d in xrange(0,len(cleaned)):
                        clean_score=clean_score+list(cleaned[d])
                #normalize the score length (10 for up to 5 sets)
                for p in range(len(clean_score),10):
                    clean_score.append('')
                
                if len(match_score_text_parsed) > 0:

                    # Tiebreaks
                    tiebreaks_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-score')]/a/sup/text()"
                    tiebreaks_parsed = xpath_parse(tourney_day_tree, tiebreaks_xpath)

                    # Fixing tiebreak problem
                    tiebreak_counter = 0
                    match_score_cleaned = []
                    tiebreak_score_cleaned = []

                    for element in match_score_text_parsed:
                        if len(element) > 0:
                            match_score_cleaned.append(regex_strip_string(element))
                            tiebreak_score_cleaned.append(regex_strip_string(element))
                        else:
                            match_score_cleaned.append("TIEBREAK")
                            tiebreak_score_cleaned.append("[" + tiebreaks_parsed[tiebreak_counter] + "]")
                            tiebreak_counter += 1
                    # Finalize match scores
                    concat_match_score = ""
                    element_count = len(match_score_cleaned)
                    for k in xrange(0,  element_count - 1):
                        concat_match_score += match_score_cleaned[k] + "::"
                    concat_match_score += match_score_cleaned[element_count - 1]
                    fix_concat_match_score = concat_match_score.replace("::TIEBREAK::", " ")
                    match_score = fix_concat_match_score.split('::')
                        
                    # Finalize tiebreak scores
                    concat_tiebreak_score = ""
                    tiebreak_element_count = len(tiebreak_score_cleaned)
                    for k in xrange(0, tiebreak_element_count - 1):
                        concat_tiebreak_score += tiebreak_score_cleaned[k] + "::"
                    concat_tiebreak_score += tiebreak_score_cleaned[element_count -1]

                    fix_concat_tiebreak_score = concat_tiebreak_score.replace("::[", "(")
                    fix_concat_tiebreak_score = fix_concat_tiebreak_score.replace("]::", ") ")    
                    tiebreak_score = fix_concat_tiebreak_score.split('::')

                    match_score = match_score[0].strip()
                    match_score_tiebreaks = tiebreak_score[0].strip()

                    winner_sets_won = 0
                    loser_sets_won = 0
                    winner_games_won = 0
                    loser_games_won = 0
                    winner_tiebreaks_won = 0
                    loser_tiebreaks_won = 0
                    match_score_split = match_score.split(' ')

                    for sets in match_score_split:
                        if len(sets) == 2:
                            if sets[0] > sets[1]:
                                winner_sets_won += 1
                                winner_games_won += int(sets[0])
                                loser_games_won += int(sets[1])
                                if sets == '76': winner_tiebreaks_won += 1

                            elif sets[0] < sets[1]:
                                loser_sets_won += 1
                                winner_games_won += int(sets[0])
                                loser_games_won += int(sets[1])
                                if sets == '67': loser_tiebreaks_won += 1

                        elif len(sets) == 3:
                            if sets == '810':
                                loser_sets_won += 1
                                loser_games_won += 10
                                winner_games_won += 8
                            elif sets == '108':
                                winner_sets_won += 1
                                winner_games_won += 10
                                loser_games_won += 8
                            elif sets == '911':
                                loser_sets_won += 1
                                loser_games_won += 11
                                winner_games_won += 9
                            elif sets == '119':
                                winner_sets_won += 1
                                winner_games_won += 11
                                loser_games_won += 9

                        elif len(sets) == 4 and sets.isdigit() == True:
                            if sets[0:1] > sets[2:3]:
                                winner_sets_won += 1
                                winner_games_won += int(sets[0:1])
                                loser_games_won += int(sets[2:3])
                            elif sets[2:3] > sets[0:1]:
                                loser_sets_won += 1
                                winner_games_won += int(sets[0:1])
                                loser_games_won += int(sets[2:3])
                    bestof=3
                    # We now guess whether it is best of 5 or best of 3
                    # it is a guess because there is 2 corner cases we cannot deduct: 
                    #   when the loser retires with total number of sets below 3 (strictly)
                    #   in the case of a W/O
                    if winner_sets_won==3 or winner_sets_won+loser_sets_won>=4 or loser_sets_won>=2 or (winner_sets_won==2 and outcome=='Retired'):
                        bestof=5
                    # in this case, we assume the same value as the previous match and hope for the best
                    if outcome=='W/O' or (winner_sets_won==1 and outcome=='Retired'):
                        if match_data!=[]:
                            bestof=match_data[-1][8]
                        
                    # Match stats URL
                    match_stats_url_xpath = tourney_match_count_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-score')]/a/@href"
                    match_stats_url_parsed = xpath_parse(tourney_day_tree, match_stats_url_xpath)
                    match_stats_url_cleaned = []
                    for element in match_stats_url_parsed:
                        if len(element) > 0:
                            match_stats_url_cleaned.append(regex_strip_string(element))
                        else:
                            match_stats_url_cleaned.append("TIEBREAK")
                        
                    if len(match_stats_url_cleaned) > 0:
                        match_stats_url_suffix = match_stats_url_cleaned[0]
                        match_stats_url_suffix_split = match_stats_url_suffix.split('/')
                        #tourney_long_slug = match_stats_url_suffix_split[3]
                        #tourney_match_id = match_stats_url_split[10]
                        match_urls.append(match_stats_url_suffix)
                    else:
                        match_stats_url_suffix = ''
                        tourney_long_slug = ''


                # Let's gather the odds for the match
                odds_found=False
                
                # We use the levenshtein distance to measure similarity between names (max 3 characters can be different)
                threshold=4
                win_odds=winner_name
                los_odds=loser_name
                # We try yesterday's odds first
                for a in xrange(0,len(odds_yes)):
                    if levenshtein_distance(odds_yes[a][0],win_odds)<threshold and levenshtein_distance(odds_yes[a][1],los_odds)<threshold:
                        oddsw=odds_yes[a][2]
                        oddsl=odds_yes[a][3]
                        odds_found=True
                        break
                    elif levenshtein_distance(odds_yes[a][1],win_odds)<threshold and levenshtein_distance(odds_yes[a][0],los_odds)<threshold:
                        oddsw=odds_yes[a][3]
                        oddsl=odds_yes[a][2]
                        odds_found=True
                        break
                # We try today's odds if still no luck
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
                    print('Odds not found for match :'+win_odds+' - '+los_odds+' on date: '+today.strftime('%Y.%m.%d')+'\nurl:https://www.oddsportal.com/matches/tennis/'+today.strftime('%Y%m%d')+'/')
                    oddsl=''
                    oddsw=''


                # Store data
                match_data.append([today.strftime('%m/%d/%Y'), tourney_round_name, bestof, winner_name, loser_name, winner_atp, loser_atp, '', '']+clean_score+[winner_sets_won, loser_sets_won, outcome, oddsw, oddsl])
                #time.sleep(.100)       


    if retrieve_planned_matches:
        # Retrieve future matches and matches that have not finished yet
        tourney_url.replace("results","daily-schedule")
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
            # We check that we are in the scraping window
            if(today<start_scraping_date or today>end_scraping_date):
                continue
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
            # Tournament size - required for round computation
            size_list=xpath_parse(day_tree,"//tr/td/div/div/a/span/text()")
            tourney_size=int(regex_strip_string(size_list[0]))
            # Round - needs to be converted
            round_list=regex_strip_array(xpath_parse(day_tree,"//td[@class='day-table-round']/text()"))
            for i in xrange(len(round_list)):
                round_list[i]=convertRound(round_list[i],tourney_size)

            # score will always be null so we return an empty list of length 10
            clean_score=[]
            for p in range(len(clean_score),10):
                            clean_score.append('')
            match_data=[]
            print(label_list)

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
                            print('Odds not found for match :'+win_odds+' - '+los_odds+' on date: '+today.strftime('%Y.%m.%d')+'\nurl:https://www.oddsportal.com/matches/tennis/'+today.strftime('%Y%m%d')+'/')
                            oddsl=''
                            oddsw=''
                    match_data.append([today.strftime('%m/%d/%Y'), tourney_round_name, bestof, player1_list[n], player2_list[n], winner_atp, loser_atp, '', '']+clean_score+['', '', '', oddsw, oddsl])

    output = [match_data, match_urls]
    return output

# Retrieve player historical ranking
# we use a local csv to store all ranking history for all players to avoid multiplying the http calls
# we check in this csv file if data is available otherwise we get it online and append the local db
# the csv contains the following: Player name, Date (always a Monday), Ranking
#we have a date, player, url and greedy parameter in input
# the greedy mode must be used with caution! For speed purposes, it does not check whether the entry already exists
def getRanking(name,date,url,greedy):
    # we get the previous monday
    current_date=datetime.strptime(date,"%Y.%m.%d")
    previous_monday = current_date + relativedelta(weekday=MO(-1))
    #print("Previous monday was: "+previous_monday.strftime("%Y.%m.%d"))
    partial_row=name+","+previous_monday.strftime("%Y.%m.%d")
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
        ranking = 'NR'
    # case where player is tied (ranking finished with a T that needs to be removed)
    elif not(ranking.isdigit()):
        ranking=ranking[:-1]
    return ranking




# Main scrapping function
# Command line input
#start_year = str(sys.argv[1])
#end_year = str(sys.argv[2])
def dataScrapper(start_scraping_date,end_scraping_date):
    start_year=start_scraping_date.year
    end_year=end_scraping_date.year
    # STEP 1: Scrape year page
    tourney_match = []
    tourney_match.append(["ATP", "Location", "Tournament", "Date", "Series", "Court", "Surface", "Round", "Best Of", "Winner", "Loser", "WRank", "LRank", "WPts", "LPts", "W1", "L1", "W2", "L2", "W3", "L3", "W4", "L4", "W5", "L5","WSets", "LSets", "Comment", "PSW", "PSL"])
    for h in xrange(int(start_year), int(end_year) + 2):

        year = str(h)
        scrape_year_output = scrape_year(year,start_scraping_date,end_scraping_date)
        tourney_data_scrape = scrape_year_output[0]
        tourney_urls_scrape = scrape_year_output[1]
        print('')
        print('Scraping match info for ' + str(len(tourney_urls_scrape)) + ' tournaments for year '+ year)
        print('Year    Order    Tournament                                Matches')
        print('----    -----    ----------                                -------')
    
        for i in xrange(0 , len(tourney_urls_scrape)):
         if len(tourney_urls_scrape[i]) > 0:
                # STEP 2: Scrape tournament page    
                match_data_scrape = []
                match_urls_scrape = []
                # we ensure we reach the results page
                scrape_tourney_output = scrape_tourney(tourney_urls_scrape[i].replace("live-scores","results"),start_scraping_date,end_scraping_date)
                match_data_scrape = scrape_tourney_output[0]
                match_urls_scrape = scrape_tourney_output[1]
                # STEP 3: tourney_data + match_data
                for match in match_data_scrape:
                    foo = tourney_data_scrape[i][:3] + match[:1] + tourney_data_scrape[i][3:] + match[1:]
                    tourney_match.append(foo)

                spacing_count1 = len('Order') - len(str(tourney_data_scrape[i][0]))
                spacing1 = ''
                for j in xrange(0, spacing_count1): spacing1 += ' '

                spacing_count2 = 41 - len(tourney_data_scrape[i][1])
                spacing2 = ''
                for j in xrange(0, spacing_count2): spacing2 += ' '

                print(str(year) + '    ' + str(tourney_data_scrape[i][0]) + str(spacing1) + '    ' + str(tourney_data_scrape[i][1]) + str(spacing2) + ' ' + str(len(match_data_scrape)))
        filename = "match_scores_" + str(start_scraping_date.strftime('%Y%m%d')) + "_" + str(end_scraping_date.strftime('%Y%m%d'))
        array2csv(tourney_match, filename)
        # convert file to xlsx
        workbook = Workbook(filename + '.xlsx')
        worksheet = workbook.add_worksheet()
        with open(filename+'.csv', 'rt', encoding='utf8') as f:
            reader = csv.reader(f)
            for r, row in enumerate(reader):
                for c, col in enumerate(row):
                    worksheet.write(r, c, col)
        workbook.close()
    return 0
