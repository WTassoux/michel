from lxml import html

sample = open("xpath_file.html","r")

def xpath_parse(tree, xpath):
    result = tree.xpath(xpath)
    return result

text = sample.read()

tree = html.fromstring(text)


tourney_details_url_xpath ="//tr[contains(@class, 'tourney-result')][1]/td[3]/span[contains(@class, 'tourney-location')]/text()"
tourney_details_url_parsed = xpath_parse(tree, tourney_details_url_xpath)
tourney_details_url_parsed[0]=tourney_details_url_parsed[0].strip()
print(tourney_details_url_parsed)

tourney_surface1_url_xpath ="//tr[contains(@class, 'tourney-result')][1]/td[5]/div/div/text()"
tourney_surface1_url_parsed = xpath_parse(tree, tourney_surface1_url_xpath)
tourney_surface1_url_parsed[0]=tourney_surface1_url_parsed[0].strip()

tourney_surface2_url_xpath ="//tr[contains(@class, 'tourney-result')][1]/td[5]/div/div/span/text()"
tourney_surface2_url_parsed = xpath_parse(tree, tourney_surface2_url_xpath)
tourney_surface2_url_parsed[0]=tourney_surface2_url_parsed[0].strip()

tourney_surface=tourney_surface1_url_parsed[0]+', '+tourney_surface2_url_parsed[0]
print(tourney_surface)