### This is the demonstration file for the Chatbot

# Here we can easily give a request to the chatbot and have the answer (queried via the Web Service)

### IMPORT

# Python libraries import
import nltk
from nltk.parse import CoreNLPParser
from nltk.parse.corenlp import CoreNLPDependencyParser
from nltk.tag.stanford import StanfordNERTagger
import os
import pandas as pd

from urllib.request import urlopen
import xml.etree.ElementTree as ET
import re

import matplotlib.pyplot as plt
import numpy as np

# Generic analysis functions import
from question_type import type_of_sentence
from time_extraction import find_time
from area_extraction import find_areas
from aggregator_extraction import find_aggregators

# Specific analysis functions import
from topic_extraction import find_topic
from dimension_extraction import dimension_fill

# Utils import
from parsing_analysis import get_subtrees, get_nodes, find_links
from utils import lower_list, normalize_figures, transform_dates
from metadata_extraction import *
import utils


### PARSERS

#Generic path
path = os.getcwd()

#Java path
java_path = "C:/Program Files (x86)/Java/jre1.8.0_251/bin/java.exe"
os.environ['JAVAHOME'] = java_path

#Files of the NER
jar = os.path.join(path, "Stanford_NER/stanford-ner-4.0.0/stanford-ner.jar")
model = os.path.join(path, "Stanford_NER/stanford-ner-4.0.0/classifiers/english.muc.7class.distsim.crf.ser.gz")

#Loading the parsers
parser = CoreNLPParser(url='http://localhost:9000')
dep_parser = CoreNLPDependencyParser(url='http://localhost:9000')
ner_tagger = StanfordNERTagger(model, jar, encoding='utf8')
pos_tagger = CoreNLPParser(url='http://localhost:9000', tagtype='pos')


### PATHS

df_path = os.path.join(path, "data/Tables.csv")

### LOADING

df_tables = pd.read_csv(df_path, sep = ";")

# Creation of some dictionaries
full_name = {}
code_dict = {}
categories = {}
for id, row in df_tables.iterrows():
    full_name[row["Short Name"]] = row["Full Name"]
    code_dict[row["Short Name"]] = row["Code"]
    try :
        a = categories[row["Category"]]
    except:
        a = []
    a.append(row["Short Name"])
    categories[row["Category"]] = a

region_dict = utils.region_dict

NOW = 2020

### FUNCTIONS


#Give the tag of the element :
# <Element '{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}Codelists' at 0x00000239F4A12AE8> ----> Codelists
def get_tag(a):
    tag = re.findall(r'\}\w*$',a.tag)[0]
    return tag[1:]


url_test = "http://nsi-staging-oecd.redpelicans.com/rest/data/OECD.GOV,DF_GOV_OG,2.0/A.OUR_DAC.FR.INDEX?startPeriod=2017&endPeriod=2019&dimensionAtObservation=AllDimensions"
url_test2 = "http://nsi-staging-oecd.redpelicans.com/rest/data/OECD.GOV,DF_GOV_1,1.1/A.GGINTN.FR.S13._T._T._T.USD?startPeriod=2010&endPeriod=2018&dimensionAtObservation=AllDimensions"

# With the URL of the data on the Web Service, extract the values for the time period and return a table
# If only one year is asked, it returns a table with only one value
# All the dimensions should already be specified in the entry URL
# This function just loads the URL and explore the tree to get the values
def get_values(url):
    file = urlopen(url)
    tree = ET.parse(file)
    header, data = tree.getroot()

    years = []
    values = []

    for obs in data:
        y = 0
        v = 0
        m = 0

        for element in obs[0]:
            if (element.attrib['id'] == "TIME_PERIOD"):
                y = int(element.attrib['value'])

        v = float(obs[1].attrib['value'])

        for element in obs[2]:
            if (element.attrib['id'] == "UNIT_MULT"):
                m = pow(10,int(element.attrib['value']))

        years.append(y)
        values.append(m*v)

    return (years, values)

# Given a list of countries/regions, returns the codes of all the countries concerned
# France --> ['FR']
# Western Europe --> ['AT','BE','FR','DE','LU','NL','CH']
def get_countries_code(countries, cl):
    res = []
    for c in countries:
        if c[1] == "country":
            try :
                res.append(cl[c[0]])
            except:
                print("Pays non reconnu : ", c[0])
        elif c[1] == "region":
            pays = region_dict[c[0]]
            for p in pays:
                try :
                    res.append(cl[p])
                except:
                    pass
    return res

# Taking the names of the dimensions as input, returns the 'country situation' of the table
# The value 1 means that the countries have only one possible place [IN] : population of India
# The value 2 means that the countries have two possible places [FROM and TO] : tourism between Germany and Italy
def country_situation(dim):
    dim_names = dim.keys()
    if "REF_AREA" in dim_names:
        return 1
    elif ("REPORTING_COUNTRY" in dim_names and "COUNTERPART_COUNTRY" in dim_names):
        return 2
    else:
        return 0

# Given the dimensions, their values, the code of the table, the countries, and the time period,
# creates the final URL used to query the data
def create_url(dimensions, values, code, y1, y2, country):
    filter = []
    ctry = ["REF_AREA", "REPORTING_COUNTRY", "COUNTERPART_COUNTRY"]
    for d in dimensions:
        if d != "TIME_PERIOD":
            if (d in ctry):
                filter.append(country[d])
            else:
                filter.append(values[d])

    prefix = "http://nsi-staging-oecd.redpelicans.com/rest/data/"
    suffix = "&dimensionAtObservation=AllDimensions"

    url = prefix + code + "/" + ".".join(filter) + "?startPeriod=" + str(y1) + "&endPeriod=" + str(y2) + suffix
    return url

# Get the index of an element in a list
def get_index(elt, liste):
    for i in range(len(liste)):
        if liste[i] == elt:
            return i
    return None

# Given the dimensions and the current values (found with dimension_fill), this function
# asks the user for the remaining information (all the dimensions with the current value None)
# It displays to the user the possible values for a given dimension and asks which one to take
def complete_dims(dims,dimensions,concepts,constraints,codelists):
    for d in dims:
        if dims[d] == None:
            triplet = dimensions[d]
            print("Please specify a value for the quantity : ", concepts[triplet[1]])
            cons = constraints[d]
            cl = codelists[triplet[2]]
            for i in range(len(cons)):
                for c in cl:
                    if c[0] == cons[i]:
                        print(i, " - ", c[1])
            j = input(">> ")
            b = False
            while (not b):
                try :
                    val = cons[int(j)]
                    b = True
                except:
                    print("Incorrect input")
                    j = input(">> ")
            dims[d] = val
    return dims


### Function to call the chatbot
def chatbot(sent):

# Normalizing + Tokenizing
    sent = transform_dates(normalize_figures(sent))
    words = nltk.word_tokenize(sent)

# Parsing
    parse = next(parser.raw_parse(sent))
    parse_d = list(dep_parser.parse(nltk.word_tokenize(sent)))[0]
    ner = ner_tagger.tag(words)
    pos = list(pos_tagger.tag(words))


# Analysis

    # Type of sentence
    s_type = type_of_sentence(parse,parse_d)
    # Time
    time = find_time(ner, parse, parse_d)
    # Area
    area = find_areas(sent)
    # Comparisons & Aggregations
    try :
        agg = find_aggregators(parse, parse_d, s_type[1], s_type[3])
    except Exception as e:
        agg = ([],None)
        #print(e)



    ## Selection of the topic with the user

    maxis, topics, cat = find_topic(sent, n=3)

    good_topic = None
    choices = list(set(topics[0] + topics[1] + topics[2] + categories[cat]))

    print("Please select the most relevant topic (type the number) :")
    print()
    for i in range(len(choices)):
        print(i, " - ", full_name[choices[i]])
    n = input(">> ")
    print()
    b = False
    while (not b):
        try :
            good_topic = choices[int(n)]
            b = True
        except:
            print("Incorrect input")
            n = input(">> ")

    #print("Correct topic is : ", good_topic)


    ## Loading Metadata

    structure_prefix = "http://nsi-staging-oecd.redpelicans.com/rest/dataflow/"
    structure_suffix = "?references=all&detail=referencepartial"

    metadata_url = structure_prefix + code_dict[good_topic] + structure_suffix

    file = urlopen(metadata_url)
    tree = ET.parse(file)
    header, structure = tree.getroot()

    dimensions = get_dimensions(structure)
    codelists = get_codelists(structure)
    constraints = get_constaints(structure)
    concepts = get_concepts(structure)



    ### Returning a Value or Time series

    if (s_type[1] == "Value" and agg == ([],None)):

        # Findind the time
        year_from = time[0]
        year_to = time[1]

        if ((year_from == None) and (year_to == None)):
            year_from = NOW
            year_to = NOW


        # Filling dimensions
        dims = dimension_fill(words,good_topic,0.5)
        dims = complete_dims(dims,dimensions,concepts,constraints,codelists)


        # Finding the locations
        country = {}

        situation = country_situation(dimensions)
        location = {}
        if situation == 1:
            cl = {}
            for pays_code, pays_nom in codelists[dimensions["REF_AREA"][2]]:
                cl[pays_nom] = pays_code
            countries = get_countries_code(area[0], cl)
        elif situation == 2:
            cl1 = {}
            cl2 = {}

            for pays_code, pays_nom in codelists[dimensions["REPORTING_COUNTRY"][2]]:
                cl1[pays_nom] = pays_code
            for pays_code, pays_nom in codelists[dimensions["COUNTERPART_COUNTRY"][2]]:
                cl2[pays_nom] = pays_code

            country["REPORTING_COUNTRY"] = get_countries_code(area[0], cl1)[0]
            country["COUNTERPART_COUNTRY"] = get_countries_code(area[1], cl2)[0]
        else:
            print("Problem")

        ## Printing the results

        # data code and metadata code are almost the same, with the "/" becoming ","
        data_code = code_dict[good_topic].replace("/", ",")

        # In situation 1, there can be several countries requested, and even regions of the world
        # We have to deal with that separately as the outputs will not be the same
        if situation == 1:

            if len(countries) == 1:   #Only 1 country
                country["REF_AREA"] = countries[0]
                data_url = create_url(dimensions, dims, data_code, year_from, year_to, country)
                values = get_values(data_url)

                # One value : just print
                if year_from == year_to:
                    print("The value is : ", values[1][0])

                # A time serie : plot a graph
                else:
                    fig,ax = plt.subplots()
                    plt.plot(values[0], values[1], '-o', color = 'b')
                    plt.xticks(rotation=45)
                    plt.show()


            else:   #Several countries
                n = len(countries)
                colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']

                df_dict = {} #dictionary to create the DataFrame

                fig,ax = plt.subplots()

                # For each country, we get the values, add the serie to a plot and add the values to the dictionary for the DataFrama
                for i in range(n):
                    c = countries[i]
                    country["REF_AREA"] = c
                    data_url = create_url(dimensions, dims, data_code, year_from, year_to, country)
                    values = get_values(data_url)

                    df_val = []
                    for j in range(year_from, year_to+1):
                        idx = get_index(j, values[0])
                        if idx == None:
                            df_val.append(np.nan)
                        else:
                            df_val.append(values[1][idx])
                    df_dict[c] = df_val

                    if (n<=len(colors) and year_from!=year_to):
                        plt.scatter(values[0], values[1], color = colors[i])
                        plt.plot(values[0], values[1], color = colors[i], label = c)

                # In all cases, we print a DataFrame with all the values at the end
                col = [str(j) for j in range(year_from, year_to+1)]
                df = pd.DataFrame.from_dict(df_dict, orient = 'index', columns = col)
                print("The values are :")
                print(df)

                # And if not too many countries and there is a time serie, we plot the different graphs
                if (n<=len(colors) and year_from!=year_to):
                    ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
                    plt.show()

        # In situation 2, there are only two countries : FROM and TO
        # So we can print the value or (in case of a time serie) plot the graph
        elif situation == 2:
            data_url = create_url(dimensions, dims, data_code, year_from, year_to, country)
            values = get_values(data_url)
            if year_from == year_to:
                print("The value is : ", values[1][0])
            else:
                plt.plot(values[0], values[1], '-o', color = 'b')
                plt.xticks(rotation=45)
                plt.show()

    ### Returning a list of countries

    elif (s_type[1] == "Agr_Area"):

        data_code = code_dict[good_topic].replace("/", ",")

        world = region_dict["World"]
        country_list = []

        comparisons = agg[0]
        aggreg = agg[1]

        # Codelist for the countries
        cl = {}
        for pays_code, pays_nom in codelists[dimensions["REF_AREA"][2]]:
            cl[pays_nom] = pays_code


        # We call a comparison "complex" when the values are not compared to a country or another value but something else. In find_aggregators, this is the comparison of type 'two'

        complex_comparison = False
        for comp in comparisons:
            if comp[0] == "Two":
                complex_comparison = True

        # In the case of a complex comparison, we need to split the sentence in two parts (before and after the word "than") and do an analysis on both sides.
        if complex_comparison:
            res = {}
            if len(comparisons)>1: #Case not handled at the moment
                print("Too many comparisons")
            else:
                comp = comparisons[0]

                # Splitting the sentence and doing both analyses
                sent1, sent2 = sent.split("than")
                words1 = nltk.word_tokenize(sent1)
                words2 = nltk.word_tokenize(sent2)

                dims1 = dimension_fill(words1,good_topic,0.5)
                dims1 = complete_dims(dims1,dimensions,concepts,constraints,codelists)
                dims2 = dimension_fill(words2,good_topic,0.5)
                dims2 = complete_dims(dims2,dimensions,concepts,constraints,codelists)

                try:
                    region = comp[2]["AREA"][0]
                except:
                    region = None

                # Finding the years in the comparison (several possibilities)
                try:
                    year1 = comp[3]["TIME"]
                    year2 = comp[4]["TIME"]
                except:
                    try:
                        year1 = comp[2]["TIME"]
                        year2 = comp[2]["TIME"]
                    except:
                        year1 = NOW
                        year2 = NOW


            # Then, for each country we do the comparison of value 1 and value 2
            # And we keep the country where the comparison is true
            for c in world:
                # If no region is specified, every country is tested
                # if a region is specified, we check if the country belongs to it
                if ((region == None) or (c in region_dict[region])):
                    country = {}
                    b = 0

                    # We try to get value 1 and value 2 for the country
                    try :
                        country["REF_AREA"] = cl[c]
                        data_url1 = create_url(dimensions, dims1, data_code, year1, year1, country)
                        data_url2 = create_url(dimensions, dims2, data_code, year2, year2, country)
                        try :
                            value1 = get_values(data_url1)[1][0]
                            value2 = get_values(data_url2)[1][0]
                            #print(value1)
                            #print(value2)

                            # And then we perform the test
                            if ((comp[1] == 'sup') and (value1 > value2)):
                                b = True
                            elif ((comp[1] == 'inf') and (value1 < value2)):
                                b = True

                        # Else, we do not have the data and the country is removed
                        except:
                            b = False
                            #print("Missing data : ", c)
                    except:
                        b = False
                        #print("Missing data : ", c)

                    if b:
                        res[c] = [value1, value2]

            # We build the result DataFrame at the end and print it
            df_res = pd.DataFrame.from_dict(res, orient = 'index', columns = ["Value 1", "Value 2"])
            print(df_res)



        # If there is no complex comparisons, it is possible to deal with several comparisons in the sentence
        elif len(comparisons)>0:

            # Filling the dimensions
            dims = dimension_fill(words,good_topic,0.5)
            dims = complete_dims(dims,dimensions,concepts,constraints,codelists)

            #Finding the time in all the comparisons (if any)
            #Finding the region in all the comparisons (if any)
            #Indeed, if we have multiple comparisons, the time/area indicators will surely be in only one of them
            year = None
            region = None
            for c in comparisons:
                if year == None:
                    try:
                        year = c[2]["TIME"]
                    except:
                        pass
                if region == None:
                    try:
                        region = c[2]["AREA"]
                    except:
                        pass
            if year == None:
                year = NOW

            if (region != None and region != []):
                country_list = region_dict[region[0]]
            else:
                country_list = world

            country_list2 = []


            # Then for each comparison, we test every country remaining
            # If the comparison is true for a country, it is added to the list for the next comparison
            # At the end, we only get the list of countries that got all the comparisons true
            for comp in comparisons:
                sens = comp[1]
                comp_type = comp[0]
                #print(dims)

                country = {}

                comp_value = None

                # First we need to determine the value of comparison
                # It can be an explicit threshold or the value of another country
                if comp_type == "Threshold":
                    comp_value = comp[4]["THRESHOLD"]
                    #print("comparative value threshold : ", comp_value)
                elif comp_type == "Country":
                    comp_country = comp[4]["AREA"]
                    try:
                        country["REF_AREA"] = cl[comp_country]
                        data_url = create_url(dimensions, dims, data_code, year, year, country)
                        comp_value = get_values(data_url)[1][0]
                        print("comparative value : ", comp_value)
                    except:
                        pass

                # If we have a value, we can perform the comparisons
                if comp_value == None:
                    print("Error : comparison not understood")
                else:
                    for pays in country_list:
                        try:
                            country["REF_AREA"] = cl[pays]
                            data_url = create_url(dimensions, dims, data_code, year, year, country)
                            pays_value = get_values(data_url)[1][0]
                        except:
                            pays_value = None

                        if pays_value != None:
                            if ((sens == "sup") and (pays_value > comp_value)):
                                country_list2.append(pays)
                            elif ((sens == "inf") and (pays_value < comp_value)):
                                country_list2.append(pays)

                # country_list is the list of countries that were compared
                # country_list2 is the list of countries that succeeded the comparison

                # We then update the list for the next comparison
                country_list = country_list2
                country_list2 = []

            res_dict = {}

            # Then we can create a DataFrame with the remaining countries and their values
            for pays in country_list:
                country["REF_AREA"] = cl[pays]
                data_url = create_url(dimensions, dims, data_code, year, year, country)
                pays_value = get_values(data_url)[1][0]
                res_dict[pays] = pays_value
            df_res = pd.DataFrame.from_dict(res_dict, orient = "index", columns = ["Value"])
            # And apply an aggregation if there is one
            if aggreg != None:
                if aggreg[0] == 'sup':
                    df_res.sort_values(by = ["Value"], ascending = False, inplace = True)
                else:
                    df_res.sort_values(by = ["Value"], ascending = True, inplace = True)
                print(df_res.head(aggreg[1]))
            else:
                print(df_res)

        # If there is no comparison at all, we only check if there is a region mentioned
        # Get the values for all the countries of the region
        # Build a list with these countries and their values
        # And apply an aggregation if any
        else:
            country = {}
            res_dict = {}
            region = None
            for r in area[0]:
                if r[1] == "region":
                    region = r[0]
            if region == None:
                region = 'World'


            year = time[0]
            dims = dimension_fill(words,good_topic,0.5)
            dims = complete_dims(dims,dimensions,concepts,constraints,codelists)

            for pays in region_dict[region]:
                try:
                    country["REF_AREA"] = cl[pays]
                    data_url = create_url(dimensions, dims, data_code, year, year, country)
                    pays_value = get_values(data_url)[1][0]
                    res_dict[pays] = pays_value
                except:
                    pass
            # Creating the dataframe
            df_res = pd.DataFrame.from_dict(res_dict, orient = "index", columns = ["Value"])

            # Applying the aggregation
            if aggreg != None:
                if aggreg[0] == 'sup':
                    df_res.sort_values(by = ["Value"], ascending = False, inplace = True)
                else:
                    df_res.sort_values(by = ["Value"], ascending = True, inplace = True)
                print(df_res.head(aggreg[1]))
            else:
                print(df_res)

    ### Returning a list of years

    elif (s_type[1] == "Agr_Time"):
        pass

    # This part should be very similar to the part "List of countries", inverting the area and time dimensions
