from lxml import html
import requests
import re
import json
import csv
import sys
import time
import numbers
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures

### This web scraper will retrieve future matches and live results from the ATP World Tour website

## We define a few functions first
def array2csv(array, filename):
    csv_array = array
    csv_out = open(filename + ".csv", 'wb')
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

def scrape_year(year):
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
        tourney_name = tourney_title_cleaned[i].encode('utf-8')

        # Assign variables
        tourney_details_url_xpath = "//tr[contains(@class, 'tourney-result')][" + str(i + 1) + "]/td[8]/a/@href"
        tourney_details_url_parsed = xpath_parse(year_tree, tourney_details_url_xpath)

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
        tourney_data.append([tourney_year_id, tourney_order, tourney_slug, tourney_url_suffix])

    # Print missing info
    if len(problem_tourneys) > 0:
        print ''
        print 'Tournaments with missing match info...'
        print 'Year    Order    Tournament'
        print '----    -----    ----------'

        for tourney in problem_tourneys:
            year = tourney[0]
            tourney_order = tourney[1]
            tourney_name = tourney[2]

            spacing_count = 5 - len(str(tourney_order))
            spacing = ''
            for j in xrange(0, spacing_count):
                spacing += ' '

            print year + '    ' + str(tourney_order) + spacing +  '    ' + tourney_name    

    # Output data
    output = [tourney_data, tourney_urls]
    return output

def scrape_tourney(tourney_url_suffix):
    url_prefix = "http://www.atpworldtour.com"
    tourney_url = url_prefix + tourney_url_suffix

    url_split = tourney_url.split("/")
    tourney_slug = url_split[6]
    tourney_year = url_split[8]
    tourney_id = url_split[7]

    # Tourney tree
    tourney_tree = html_parse_tree(tourney_url)     

    tourney_round_name_xpath = "//table[contains(@class, 'day-table')]/thead/tr/th/text()"
    tourney_round_name_parsed = xpath_parse(tourney_tree, tourney_round_name_xpath)
    tourney_round_count = len(tourney_round_name_parsed)

    match_urls = []
    match_data = []

    # We figure out the dates of the tournament and try to retrieve the matches for each match
    tourney_dates_xpath = "//ul[@data-value='matchdate']/li[@data-value]/text()"
    round_match_count_parsed = xpath_parse(tourney_tree, tourney_dates_xpath)
    #round_match_count = len(round_match_count_parsed)
    print round_match_count_parsed
    # Iterate through each round    
    for i in xrange(0, tourney_round_count):
        round_order = i + 1

        tourney_round_name = tourney_round_name_parsed[i]

        #round_match_count_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr/td[contains(@class, 'day-table-score')]/a/@href"
        round_match_count_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr/td[contains(@class, 'day-table-name')][1]/a/text()"
        round_match_count_parsed = xpath_parse(tourney_tree, round_match_count_xpath)
        round_match_count = len(round_match_count_parsed)

        # Iterate through each match
        for j in xrange(0, round_match_count):
            match_order = j + 1

            # Winner
            winner_name_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-name')][1]/a/text()"
            winner_name_parsed = xpath_parse(tourney_tree, winner_name_xpath)

            winner_url_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-name')][1]/a/@href"
            winner_url_parsed = xpath_parse(tourney_tree, winner_url_xpath)

            winner_name = winner_name_parsed[0].encode('utf-8')
            winner_url = winner_url_parsed[0]
            winner_url_split = winner_url.split('/')
            winner_slug = winner_url_split[3]
            winner_player_id = winner_url_split[4]            

            # Loser
            loser_name_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-name')][2]/a/text()"
            loser_name_parsed = xpath_parse(tourney_tree, loser_name_xpath)

            loser_url_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i +1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-name')][2]/a/@href"
            loser_url_parsed = xpath_parse(tourney_tree, loser_url_xpath)

            try:
                loser_name = loser_name_parsed[0].encode('utf-8')
                loser_url = loser_url_parsed[0]
                loser_url
                loser_url_split = loser_url.split('/')
                loser_slug = loser_url_split[3]
                loser_player_id = loser_url_split[4]
            except Exception:
                loser_name = ''
                loser_url = ''
                loser_slug = ''
                loser_player_id = ''

            # Seeds
            winner_seed_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-seed')][1]/span/text()"
            winner_seed_parsed = xpath_parse(tourney_tree, winner_seed_xpath)
            winner_seed_cleaned = regex_strip_array(winner_seed_parsed)
            if len(winner_seed_cleaned) > 0:
                winner_seed = winner_seed_cleaned[0]
            else:
                winner_seed = ''
            winner_seed = winner_seed.replace('(', '')
            winner_seed = winner_seed.replace(')', '')
            
            loser_seed_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-seed')][2]/span/text()"        
            loser_seed_parsed = xpath_parse(tourney_tree, loser_seed_xpath)
            loser_seed_cleaned = regex_strip_array(loser_seed_parsed)
            if len(loser_seed_cleaned) > 0:
                loser_seed = loser_seed_cleaned[0]
            else:
                loser_seed = ''
            loser_seed = loser_seed.replace('(', '')
            loser_seed = loser_seed.replace(')', '')        

            # Match score
            match_score_text_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-score')]/a/node()"
            match_score_text_parsed = xpath_parse(tourney_tree, match_score_text_xpath)

            if len(match_score_text_parsed) > 0:

                # Tiebreaks
                tiebreaks_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-score')]/a/sup/text()"
                tiebreaks_parsed = xpath_parse(tourney_tree, tiebreaks_xpath)

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

                # Match id
                match_id = tourney_year + "-" + tourney_id + "-" + winner_player_id + "-" + loser_player_id
                                        
                # Match stats URL
                match_stats_url_xpath = tourney_match_count_xpath = "//table[contains(@class, 'day-table')]/tbody[" + str(i + 1) + "]/tr[" + str(j + 1) + "]/td[contains(@class, 'day-table-score')]/a/@href"
                match_stats_url_parsed = xpath_parse(tourney_tree, match_stats_url_xpath)
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
                match_data.append([tourney_round_name, round_order, match_order, winner_name, winner_player_id, winner_slug, loser_name, loser_player_id, loser_slug, winner_seed, loser_seed, match_score_tiebreaks, winner_sets_won, loser_sets_won, winner_games_won, loser_games_won, winner_tiebreaks_won, loser_tiebreaks_won, match_id, match_stats_url_suffix])
                #time.sleep(.100)       

    output = [match_data, match_urls]
    return output

# Main scrapping function
# Command line input
#start_year = str(sys.argv[1])
#end_year = str(sys.argv[2])
def dataScrapper(start_year,end_year):
    # STEP 1: Scrape year page
    tourney_match = []
    for h in xrange(int(start_year), int(end_year) + 1):

        year = str(h)
        scrape_year_output = scrape_year(year)
        tourney_data_scrape = scrape_year_output[0]
        tourney_urls_scrape = scrape_year_output[1]
        print ''
        print 'Scraping match info for ' + str(len(tourney_urls_scrape)) + ' tournaments...'
        print 'Year    Order    Tournament                                Matches'
        print '----    -----    ----------                                -------'
    
        for i in xrange(0 , len(tourney_urls_scrape)):
         if len(tourney_urls_scrape[i]) > 0:
                # STEP 2: Scrape tournament page    
                match_data_scrape = []
                match_urls_scrape = []
                scrape_tourney_output = scrape_tourney(tourney_urls_scrape[i])
                match_data_scrape = scrape_tourney_output[0]
                match_urls_scrape = scrape_tourney_output[1]
                # STEP 3: tourney_data + match_data
                for match in match_data_scrape:
                    foo = tourney_data_scrape[i] + match
                    tourney_match.append(foo)

                spacing_count1 = len('Order') - len(str(tourney_data_scrape[i][1]))
                spacing1 = ''
                for j in xrange(0, spacing_count1): spacing1 += ' '

                spacing_count2 = 41 - len(tourney_data_scrape[i][2])
                spacing2 = ''
                for j in xrange(0, spacing_count2): spacing2 += ' '

                print year + '    ' + str(tourney_data_scrape[i][1]) + spacing1 + '    ' + tourney_data_scrape[i][2] + spacing2 + ' ' + str(len(match_data_scrape))
        filename = "match_scores_" + str(start_year) + "-" + str(end_year)
        array2csv(tourney_match, filename)
    return 0