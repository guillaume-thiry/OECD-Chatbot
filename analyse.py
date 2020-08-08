### This is the main file of the Chatbot

# It contains a function 'analyse' that reproduce the pipeline of the algorithm to treat a given query
# To do that, it calls various different analysis functions from the other files of the code
# At the moment, we only do the Natural Language Analysis, without the final query and display of the data
# First because we lack data to have a meaningful and functional Chatbot
# Seconde because this part will surely imply a graphic interface to interact with the user (which is out of our scope)

# Then, a set of tests have been implemented to allows for an easy assessment of each part of the code separately
# Those can be executed directly at the end of the code

### IMPORT

# Python libraries import
import nltk
from nltk.parse import CoreNLPParser
from nltk.parse.corenlp import CoreNLPDependencyParser
from nltk.tag.stanford import StanfordNERTagger
import os
import pandas as pd


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


### PARSERS

#Generic path
path = os.getcwd()

#Java path (to be changed)
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

#Type test
type_test_input = os.path.join(path, "data/test/Sentence_type_queries_test.csv")
type_test_output = os.path.join(path, "data/test/Sentence_type_queries_results.csv")

#Date-Location test
time_loc_test_input = os.path.join(path, "data/test/Time_Location_queries_test.csv")
time_loc_test_output = os.path.join(path, "data/test/Time_Location_queries_results.csv")

#Comp test
comp_test_input = os.path.join(path, "data/test/Comp_queries_test.csv")
comp_test_output = os.path.join(path, "data/test/Comp_queries_results.csv")

#Sup test
sup_test_input = os.path.join(path, "data/test/Sup_queries_test.csv")
sup_test_output = os.path.join(path, "data/test/Sup_queries_results.csv")

#Topic test
topic_test_input = os.path.join(path, "data/test/Topic_queries_test.csv")
topic_test_output = os.path.join(path, "data/test/Topic_queries_results.csv")

#Dimension test
dimension_test_input = os.path.join(path, "data/test/Dimensions_queries_test.csv")
dimension_test_output = os.path.join(path, "data/test/Dimensions_queries_results.csv")


### EXAMPLE ANALYSIS

# WARNING : this function does all the analysis but still displays results that are quite computer-readable
# These results will be the inputs given to a final query function, which will have to query the system for the data, and displays it to the user

def analyse(sent):

# Normalizing + Tokenizing
    sent = transform_dates(normalize_figures(sent))
    words = nltk.word_tokenize(sent)

# Parsing
    parse = next(parser.raw_parse(sent))
    parse_d = list(dep_parser.parse(nltk.word_tokenize(sent)))[0]
    ner = ner_tagger.tag(words)
    pos = list(pos_tagger.tag(words))

    # Parses printing
    #parse.pretty_print()
    #parse_d.tree().pretty_print()
    #print(ner)
    #print(pos)

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
        agg = [[],None]
        #print(e)

    #Topic
    maxis, topics, cat = find_topic(sent, n=3)
    #Dimensions
    dims = dimension_fill(words,topics[0][0],0)

    print("#####")
    print("ANALYSIS OF : " ,  sent)
    print()
    print("Type of sentence : ", s_type)
    print()
    print("Time : ", time)
    print()
    print("Ares : ", area)
    print()
    print("Comparisons : ", agg[0])
    print()
    print("Aggregations : ", agg[1])
    print()
    print("## WARNING : the quality of this part really depends on the available data :")
    print()
    print("Topics : ", topics)
    print()
    print("Category : ", cat)
    print()
    print("Dimensions : ", dims)
    print()
    print("#####")
    print()


# Set of 80 queries to test the analysis pipeline

example_queries_path = os.path.join(path, "data/Queries.txt")
f = open(example_queries_path, "r")
example_queries = []
q = f.readline()

while (q != ""):
    example_queries.append(q.replace('\n', ''))
    q = f.readline()

#for sent in example_queries:
#    analyse(sent)


### Testing : Find the type of sentence

def type_test():
    df_type = pd.read_csv(type_test_input, sep = ';')
    print("Loading queries from 'Sentence_type_queries_test.csv'")
    # Scores
    n = 0
    i = 0
    j = 0
    k = 0
    l = 0

    for id, row in df_type.iterrows():
        # Loading of the sentence, normalizing, parsing
        sent = row["Query"]
        sent = transform_dates(normalize_figures(sent))
        n+=1

        parse = next(parser.raw_parse(sent))
        parse_d = list(dep_parser.parse(nltk.word_tokenize(sent)))[0]

        # Type of sentence
        t = type_of_sentence(parse,parse_d)
        try:
            agg = find_aggregators(parse,parse_d, t[1], t[3])
        except Exception as e:
            agg = [[],None]
            print(e)

        val = t[1]
        if t[1] == "Value":
            if (len(agg[0])>0 or agg[1]!= None):
                val = "Agr_Area"

        # Assessment and scoring

        if t[0] == row["Type"]:
            i+=1
            df_type.at[id,"Correct type"] = 1
        else:
            df_type.at[id,"Correct type"] = 0


        if val == row["Returned"]:
            j+=1
            df_type.at[id,"Correct return"] = 1
        else:
            df_type.at[id,"Correct return"] = 0


        if ((len(agg[0])>0 and row["Comp"] == 1) or (len(agg[0])==0 and row["Comp"] == 0)):
            k+=1
            df_type.at[id,"Correct comp"] = 1
        else:
            df_type.at[id,"Correct comp"] = 0


        if ((agg[1]==None and row["Sup"] == 0) or (agg[1]!=None and row["Sup"] == 1)):
            l+=1
            df_type.at[id,"Correct sup"] = 1
        else:
            df_type.at[id,"Correct sup"] = 0

    # Saving
    df_type.to_csv(type_test_output, index = False)
    print("Saving results in 'Sentence_type_queries_results.csv'")

    # Displaying the results
    print()
    print("Accuracy type : ", i/n)
    print("Accuracy return : ", j/n)
    print("Accuracy comp : ", k/n)
    print("Accuracy sup : ", l/n)


### Testing : Find the time and the location

def time_loc_test():
    df_timeloc = pd.read_csv(time_loc_test_input, sep = ';')
    print("Loading queries from 'Time_Location_queries_test.csv'")

    # Scores
    t = 0
    l = 0
    n = 0

    for id, row in df_timeloc.iterrows():
        # Loading of the sentence, normalizing, parsing
        n = n+1
        sent = row["Query"]
        sent = transform_dates(normalize_figures(sent))

        words = nltk.word_tokenize(sent)

        parse = next(parser.raw_parse(sent))
        parse_d = list(dep_parser.parse(nltk.word_tokenize(sent)))[0]
        ner = ner_tagger.tag(words)

        # Time and location analysis

        time = find_time(ner, parse, parse_d)
        loc = find_areas(sent)
        type = type_of_sentence(parse,parse_d)

        df_timeloc.at[id,"Time"] = str(time)
        df_timeloc.at[id,"Loc"] = str(loc)

        correct_time = 0

        date_from = time[0]
        date_to = time[1]

        if date_from == None:
            if type[1] == "Agr_Time":
                date_from = 1900
            else:
                date_from = 2020
        if date_to == None:
            date_to = 2020


        loc_from = []
        loc_to = []
        loc_than = []
        for a in loc[0]:
            loc_from.append(a[0])
        for b in loc[1]:
            loc_to.append(b[0])
        for c in loc[2]:
            loc_than.append(c[0])

        loc_from = "/".join(loc_from)
        loc_to = "/".join(loc_to)
        loc_than = "/".join(loc_than)

        if loc_from == '':
            loc_from = 'None'
        if loc_to == '':
            loc_to = 'None'
        if loc_than == '':
            loc_than = 'None'

         # Assessment and scoring of time

        if (date_from==int(row["Date_from"]) and date_to==int(row["Date_to"])):
            if row["Date_than"] == "None":
                if time[2] == []:
                    correct_time = 1
            else:
                if len(time[2])==1:
                    if int(row["Date_than"]) == time[2][0]:
                        correct_time = 1

        t += correct_time
        df_timeloc.at[id, "Correct time"] = correct_time

        correct_loc = 0

        if ((loc_from == row["Loc_from"]) and (loc_to == row["Loc_to"]) and (loc_than == row["Loc_than"])):
            correct_loc = 1

        l += correct_loc
        df_timeloc.at[id, "Correct loc"] = correct_loc


    # Saving
    df_timeloc.to_csv(time_loc_test_output, index = False)
    print("Saving results in 'Time_Location_queries_test.csv'")

    # Displaying the results
    print()
    print("Time accuracy : ", t/n)
    print("Loc accuracy : ", l/n)


### Testing : Find the comparison

def comp_test():
    df_comp = pd.read_csv(comp_test_input, sep = ';')
    print("Loading queries from 'Comp_queries_test.csv'")
    print()


    for id, row in df_comp.iterrows():
        # Loading of the sentence, normalizing, parsing
        sent = row["Query"]
        sent = transform_dates(normalize_figures(sent))

        parse = next(parser.raw_parse(sent))
        parse_d = list(dep_parser.parse(nltk.word_tokenize(sent)))[0]

        # Comparison analysis
        t = type_of_sentence(parse,parse_d)
        ret = t[1]
        try:
            agg = find_aggregators(parse,parse_d, t[1], t[3])
        except Exception as e:
            agg = [[],None]
            print(e)
            print(sent)
            print(t)
            print()
        if len(agg[0])>0 and ret == "Value":
            ret = "Agr_Area"
        df_comp.at[id, "Comparison"] = ret + " // " + str(agg[0])

    # Saving
    print()
    df_comp.to_csv(comp_test_output, index = False)
    print("Saving results in 'Comp_queries_test.csv'")

    # Assessment is done by hand here


### Testing : Find the aggregation

def sup_test():
    df_sup = pd.read_csv(sup_test_input, sep = ';')
    print("Loading queries from 'Sup_queries_test.csv'")
    print()
    s = 0
    v = 0
    n = 0

    for id, row in df_sup.iterrows():
        # Loading of the sentence, normalizing, parsing
        n+=1
        sent = row["Query"]
        sent = transform_dates(normalize_figures(sent))

        parse = next(parser.raw_parse(sent))
        parse_d = list(dep_parser.parse(nltk.word_tokenize(sent)))[0]

        # Aggregation analysis
        t = type_of_sentence(parse,parse_d)
        ret = t[1]
        try:
            agg = find_aggregators(parse,parse_d, t[1], t[3])
        except Exception as e:
            agg = [[],None]
            print(e)
            print(sent)
            print(t)
            print()

        # Assessment and scoring
        if agg[1][0] == row["Sens"]:
            df_sup.at[id, "Correct sens"] = 1
            s+=1
        else:
            df_sup.at[id, "Correct sens"] = 0

        if agg[1][1] == int(row["Value"]):
            df_sup.at[id, "Correct value"] = 1
            v+=1
        else:
            df_sup.at[id, "Correct value"] = 0

    # Saving
    df_sup.to_csv(sup_test_output, index = False)
    print("Saving results in 'sup_queries_test.csv'")

    # Displaying the results
    print()
    print("Accuracy sens : ", s/n)
    print("Accuracy value", v/n)


### Testing : Find the topic

def topic_test():
    df_queries = pd.read_csv(topic_test_input, sep = ';')
    print("Loading queries from 'Topic_queries_test.csv'")

    n = 0
    for id, row in df_queries.iterrows():
        # Loading of the sentence, normalizing, parsing
        if row["Table"] != 'None':
            n += 1
        query = row["Query"]

        # Topic analysis
        maxi, topics, category = find_topic(query, n=3)

        text1 = ' / '.join(topics[0])
        df_queries.at[id, "Number 1"] = text1

        text2 = ' / '.join(topics[1])
        df_queries.at[id, "Number 2"] = text2

        text3 = ' / '.join(topics[2])
        df_queries.at[id, "Number 3"] = text3

        df_queries.at[id, "Predicted Cat"] = category

        df_queries.at[id,"Best scores"] = str(maxi)


        # Assessment
        true_table = row["Table"]
        true_cat = row["Category"]
        df_queries.at[id, "Top1"] = int(true_table in topics[0])
        df_queries.at[id, "Top3"] = int((true_table in topics[0]) or (true_table in topics[1]) or (true_table in topics[2]))
        df_queries.at[id, "Cat"] = int(true_cat == category)

    # Saving
    df_queries.to_csv(topic_test_output, index = False)
    print("Saving results in 'Topic_queries_results.csv'")

    # Scoring
    percent1 = 0
    percent3 = 0
    percentcat = 0
    atleast = 0

    for i in range(n):
        percent1 += df_queries.at[i,"Top1"]
        percent3 += df_queries.at[i,"Top3"]
        percentcat += df_queries.at[i,"Cat"]
        if ((df_queries.at[i, "Top1"]+df_queries.at[i,"Top3"]+df_queries.at[i,"Cat"])>0):
            atleast += 1

    # Displaying the results
    percent1 /= n
    percent3 /= n
    percentcat /= n
    atleast /= n
    print()
    print("Accuracy top 1 : ", percent1)
    print("Accuracy top 3 : ", percent3)
    print("Accuracy category : ", percentcat)
    #print("At least one : ", atleast)


### Testing : Fill the dimensions

def dimension_test(seuil=0):
    df_dim = pd.read_csv(dimension_test_input, sep = ";")
    print("Loading queries from 'Dimensions_queries_test.csv'")
    res = 0
    n = 0

    for id, row in df_dim.iterrows():
        # Loading of the sentence, normalizing, parsing
        topic = row["Table"]
        than = int(row["Than"])
        dim = row["Dimension"]
        val = row["Value"]
        sent = row["Query"]
        sent = sent.replace("-", " ")

        # Dimension filling
        # We differentiate the case with a "than" and without
        # Because if there is a "than", we do 2 "dimension fill", one for each part of the comparison
        if than :
            n += 2
            s = sent.split("than")
            r = 0
            w0 = nltk.word_tokenize(s[0])
            w1 = nltk.word_tokenize(s[1])
            pred0 = dimension_fill(w0,topic,seuil)
            pred1 = dimension_fill(w1, topic,seuil)
            v = val.split('/')

            # Assessment
            if v[0] == pred0[dim]:
                r += 1
                res += 1
            if v[1] == pred1[dim]:
                r += 1
                res += 1
            df_dim.at[id,"Result"] = r

        else:
            n += 1
            words = nltk.word_tokenize(sent)
            fill = dimension_fill(words,topic,seuil)
            predict = fill[dim]

            # Assessment
            if val == predict:
                df_dim.at[id,"Result"] = 1
                res += 1
            else:
                df_dim.at[id,"Result"] = 0
                print(sent)
                print(topic)
                print(val)
                print(predict)
                print()

    # Saving
    df_dim.to_csv(dimension_test_output, index = False)
    print("Saving results in 'Dimensions_queries_results.csv'")

    # Displaying the results
    print()
    print("Accuracy : ", res/n*100)




### EXECUTIONS


type_test()
time_loc_test()
comp_test()
sup_test()
topic_test()
dimension_test()