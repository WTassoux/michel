###################################################################
#
#
#				DATA MANAGEMENT AND COMPUTATION
#
#
###################################################################
#
#	This tool will be:
#		- Gathering new data online
#		- Formatting the data
#		- Computing additional hyper parameters
#		- Maintain a database of the past data
#
import glob
import pandas
import numpy



# We check if more data is available online

# def dataScrapper():

### TODO ###
# Check online for additional data (once a day?/everytime this script is called)
# Append the csv/xls file with collected data of the day if not already imported
# 
# Need to import ALL ATP matches, including challengers to gather more data (esp. for players ranked between 50 and 250)


# We import all gathered data
def dataCleaner():
    #filenames=list(glob.glob("Data/[0-9]^4.xls*"))
    filenames=list(glob.glob("TestData/20*.xls*"))
    data=[pandas.read_excel(filename) for filename in filenames]

    # Some odds are missing and we need to clean the data
    # Only pinnacle odds are treated as they are deemed the most accurate
    no_pinnacle_odd=[i for i,d in enumerate(data) if "PSW" not in data[i].columns]
    for i in no_pinnacle_odd:
        data[i]["PSW"]=numpy.nan
        data[i]["PSL"]=numpy.nan
    
    #We only keep the following columns: ATP/Location/Tournament/Date/Series/Court/Surface/Round/Bestof/Winner/Loser/WRank/LRank/Wsets/Lsets/Comment/PSW/PSL
    data=[x[list(x.columns)[:13]+["Wsets","Lsets","Comment"]+["PSW","PSL"]] for x in data]
    dataset=pandas.concat(data)
    
    # The data needs to be cleaned a bit
    
    # First, we  sort by date
    dataset=dataset.sort_values("Date")
    
    # Some rankings are not provided. In this case we specify Non Ranked people as (NR) as ranked 2000 and N/A is for people with wildcards. We leave it as is
    dataset["WRank"]=dataset["WRank"].replace("NR",2000)
    dataset["LRank"]=dataset["LRank"].replace("NR",2000)
    dataset["WRank"]=dataset["WRank"].astype(int)
    dataset["LRank"]=dataset["LRank"].astype(int)
    dataset["Wsets"]=dataset["Wsets"].astype(int)
    dataset["Lsets"]=dataset["Lsets"].replace("`1",1)
    dataset["Lsets"]=dataset["Lsets"].astype(int)
    dataset=dataset.reset_index(drop=True)
    return dataset
