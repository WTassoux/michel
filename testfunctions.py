###################################################################
#
#
#				        TEST FUNCTIONS
#
#
###################################################################

def testRankingAccuracy(df, column_lesser, column_greater):
    """
    This function tests the accuracy of a ranking algorithm
    It takes the difference in ranking and checks whether the match outcome reflects is
    The function returns the percentage of the matches that were correctly predicted
    """
    count = 0
    for index, row in df.iterrows():
        if (row[column_lesser]<row[column_greater]):
            count+=1
    return float(count)/float(len(df))
