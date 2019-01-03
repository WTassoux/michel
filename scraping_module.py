from lxml import html
import requests
import re
import json
import csv
import sys
import time
from datetime import timedelta, datetime
import numbers
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures

# Python 2 backwards compatibility
try:
    # Python 2
    xrange
except NameError:
    # Python 3, xrange is now named range
    xrange = range


### This web scraper will retrieve future matches and live results from the ATP World Tour website

## We define a few functions first
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
        if(tourney_enddate<start_scraping_date or tourney_startdate>end_scraping_date):
            continue
        
        # Assign variables
        tourney_details_url_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[8]/a/@href"
        tourney_details_url_parsed = xpath_parse(year_tree, tourney_details_url_xpath)
        #print(tourney_details_url_parsed)

        tourney_location_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[3]/span[contains(@class, 'tourney-location')]/text()"
        tourney_location =xpath_parse(year_tree, tourney_location_xpath)
        tourney_location=tourney_location[0].strip()
        #print(tourney_location)
        tourney_surface1_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[5]/div/div[contains(@class, 'item-details')]/text()"
        tourney_surface1 = xpath_parse(year_tree, tourney_surface1_xpath) 
        tourney_surface2_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[5]/div/div/span[contains(@class, 'item-value')]/text()"
        tourney_surface2 = xpath_parse(year_tree, tourney_surface2_xpath)
        tourney_surface =  tourney_surface1[0].strip()+', '+tourney_surface2[0].strip()
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
        tourney_data.append([tourney_order, tourney_location, tourney_name, tourney_surface, tourney_class])

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
    
    #match_data.append(["Date", "Round", "Winner", "Loser", "Score", "Winner Sets Won", "Loser Sets Won", "Winner Total Games", "Loser Total Games", "Winner Tie-Breaks", "Loser Tie-Breaks"])
    # We figure out the dates of the tournament and try to retrieve the matches for each day
    # This only works for the current year. Past years do not have dates and the iteration needs to be through the rounds directly
    tourney_dates_xpath = "//ul[@data-value='matchdate']/li[@data-value]/text()"
    day_count_parsed = xpath_parse(tourney_tree, tourney_dates_xpath)
    day_match_count = len(day_count_parsed)
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
            
            round_order = i + 1

            tourney_round_name = tourney_round_name_parsed[i]

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
                #winner_url = winner_url_parsed[0]
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
                    #loser_url = loser_url_parsed[0]
                    #loser_url_split = loser_url.split('/')
                    #loser_slug = loser_url_split[3]
                    #loser_player_id = loser_url_split[4]
                # this exeption needs to be handled somehow - not sure when this happens
                except Exception:
                    loser_name = ''
                    #loser_url = ''
                    #loser_slug = ''
                    #loser_player_id = ''

                # Match score
                match_score_text_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-score')]/a/node()"
                match_score_text_parsed = xpath_parse(tourney_day_tree, match_score_text_xpath)

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

                # Store data
                match_data.append([today.strftime('%Y-%m-%d'), tourney_round_name, winner_name, loser_name, match_score_tiebreaks, winner_sets_won, loser_sets_won, winner_games_won, loser_games_won, winner_tiebreaks_won, loser_tiebreaks_won])
                #time.sleep(.100)       

    output = [match_data, match_urls]
    return output

# Main scrapping function
# Command line input
#start_year = str(sys.argv[1])
#end_year = str(sys.argv[2])
def dataScrapper(start_scraping_date,end_scraping_date):
    start_year=start_scraping_date.year
    end_year=end_scraping_date.year
    # STEP 1: Scrape year page
    tourney_match = []
    tourney_match.append(["ATP", "Location", "Tournament", "Surface", "Class", "Date", "Round", "Winner", "Loser", "Score", "Winner Sets Won", "Loser Sets Won", "Winner Total Games", "Loser Total Games", "Winner Tie-Breaks", "Loser Tie-Breaks"])
    for h in xrange(int(start_year), int(end_year) + 1):

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
                    foo = tourney_data_scrape[i] + match
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
    return 0
