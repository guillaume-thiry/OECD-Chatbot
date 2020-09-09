#  @ Copyright Inria, Ecole Polytechnique
#  Shared under the MIT license https://opensource.org/licenses/mit-license.php

# This file contains all the functions that are used in the time detection
# The main part of the code is the function find_time, that will be used elsewhere in the code
# The other functions are auxiliary that are being used in the main one

### IMPORT

# Utils import
from parsing_analysis import get_subtrees, find_links
from utils import lower_list, get_index

### FUNCTIONS

BEGINNING = 1900
NOW = 2020

# This first function determines if a word fits the year format
# For it to be a year, it needs to be a :
# i)   an integer
# ii)  higher than 1900
# iii) lower or equal than the current year (2020)

def year_format(y):
    try :
        year = int(y)
        b = (BEGINNING < year and year <= NOW)
        return b
    except :
        return False

durations_s = {"year" : 1, "decade" : 10, "century" : 100}
durations_p = {"years" : 1, "decades" : 10, "centuries" : 100}

# This function finds duration words (like "years" or "decade") in a list of tokens
# And returns the number of years of this duration (and if the word is singular or plural)

def get_duration(liste):
    for a in liste:
        if a in list(durations_s.keys()):
            return (durations_s[a], 's')
        if a in list(durations_p.keys()):
            return (durations_p[a], 'p')
    return None

# This function takes as inputs three parsers
# and returns all the numbers in the sentence which are describing a data

def date_figures(ner, pos, dep):
    n = len(ner)
    res = []
    for i in range(n):
        # First, the word has to be a number ("CD" tag in the POS tagging)
        if pos[i][1] == "CD":
            # Then, we try to see if it is a date
            b = False
            # either it is considered as a date by the NER
            if ner[i][1] == "DATE":
                b = True
            # or it is linked (in the dependency parser) to a date (NER)
            else:
                links = find_links(dep, pos[i][0])
                for l in links:
                    for ner_w in ner:
                        if (ner_w[0] == l and ner_w[1] == "DATE"):
                            b = True
            if b:
                res.append(ner[i][0])
    return res

# The function find_time identifies all the dates of the sentence, as well as their contexts
# Three categories are possible : FROM / TO / THAN
# THAN corresponds to all the dates written after a "than"
# As explained in area_extraction, it will be determined later (in find_aggregators) if the date is or is not part of a comparison
# Else, FROM and TO determine the time period covered in the query (they are equal if the user only wants one specific year)
# This function also detects sentences like "over the last 5 years" and calculate the years it corresponds to

def find_time(ner, parse, parse_d):

    n = len(ner)
    res = []

    date_from = None
    date_to = None
    date_than = []

    # First, we look at the dates detected by the NER
    for i in range(n):
        if ner[i][1] == "DATE":
            res.append(ner[i][0])

    pps = get_subtrees(parse, "PP")

    # the dates that are years are put in the list years
    years = []
    for a in res:
        if year_format(a):
            years.append(a)
    for b in years:
        res.remove(b)
    tok = parse.leaves()

    # if there is a "than" and years placed after that, they go in date_than
    # and they are removed from years
    if ('than' in tok):
        idx = get_index(tok, 'than')
        for i in range(len(years)):
            if get_index(tok, years[i])>idx:
                date_than.append(int(years[i]))
    for b in date_than:
        years.remove(str(b))

    # if only 1 year remains, we look at its context
    if len(years) == 1:
        y = years[0]
        link = None
        # the context of a year will often be the Prepositional Phrase (PP) it belongs to
        for pp in pps:
            if y in pp.leaves():
                link = pp.leaves()
        # if no PP was found, we can also look at the words linked to the year in the dependency structure
        if link == None:
            link = find_links(parse_d, y)
        # and then, depending on the words found in the context of the year, we know its function
        if link != []:
            lower_link = lower_list(link)
            if 'in' in lower_link:
                date_from = int(y)
                date_to = int(y)
            # for example, if the year is associated with 'since' (like in "Population in Iran since 1960"), it will be the DATE_FROM
            elif 'since' in lower_link:
                date_from = int(y)
            elif 'after' in lower_link:
                date_from = int(y)
            elif 'till' in lower_link:
                date_to = int(y)
            elif 'before' in lower_link:
                date_to = int(y)
            else:
                date_from = int(y)
                date_to = int(y)
    # if we have 2 years or more, we take the minimum and maximum to have the time period
    elif len(years) >= 2:
        date_from = min(int(years[0]),int(years[1]))
        date_to = max(int(years[0]),int(years[1]))

    # if we have no years but other things tagged as a date
    # we try to find a duration (like in "over the last 8 decades")
    elif res != []:
        duration = 0
        lowered = lower_list(res)
        fig = []
        # we need to have the word "last"
        if "last" in res:
            # Now we know that we probably have a stucture "over the last ..."
            # We can try to find a figure (like the number of years)

            # first, we try to find numbers in the words tagged as dates (they are obviously not years here)
            for r in res:
                try:
                    b = int(r)
                    fig.append(b)
                except:
                    pass

            # if no numbers was found, we try to find a PP containing all the words of the date
            if fig == []:
                pp_date = None

                for pp in pps:
                    c = True
                    leaves = lower_list(pp.leaves())
                    for l in lowered:
                        if l not in leaves:
                            c = False
                    if c == True:
                        pp_date =  lower_list(pp.leaves())
                # and if such a PP was found, we try to find numbers in it
                if pp_date != None:
                    if 'last' in pp_date:
                        for a in pp_date:
                            try:
                                b = int(a)
                                fig.append(b)
                            except:
                                pass

            # if no numbers was found, it will be 1

            n = 1
            if len(fig)==1:
                n = fig[0]

            # now we try to find duration words (with the function)
            dur = get_duration(res)

            # if such a word was found, we take its duration and multiply it by the number found
            # therefore, "8 decades" will be 80 while "5 centuries" will be 500
            if dur != None:
                # if no number was found (hence the default value of 1), it depends whether the word is singular or plural
                # for plural, the default value is 5
                # over the last decades = 50, over the last 3 decades = 30, over the last decade = 10
                if n==1:
                    if dur[1] == 's':
                        duration = dur[0]
                    elif dur[1] == 'p':
                        duration = dur[0]*5
                else:
                    duration = dur[0]*n
                if duration > 0:
                    date_to = NOW
                    date_from = NOW-duration

    return (date_from,date_to, date_than)
