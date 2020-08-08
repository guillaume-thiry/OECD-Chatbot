# This file contains all the functions that are used in the topic finding
# The final function 'find_topic' is used elsewhere in the chatbot
# and uses many different other functions to compute the proximity scores and rank them

### IMPORT

# Python libraries import
import pickle
import nltk
from nltk.corpus import stopwords
import pandas as pd
import os


from word_proximity import proximity
from utils import is_word


### PATHS

path = os.getcwd()

df_path = os.path.join(path, "data/Tables.csv")
topic_path = os.path.join(path, "data/topic_dict.pkl")

### LOADINGS

df_tables = pd.read_csv(df_path, sep = ";")

# List of table names and categories
name_list = []
cat_list = []
for id, row in df_tables.iterrows():
    name_list.append(row["Short Name"])
    cat_list.append(row["Category"])

N = len(name_list)

#keywords dictionary
file = open(topic_path, "rb")
keywords = pickle.load(file)
file.close()


### FUNCTIONS

coef = (1,0.6,0.6,0.6)

# This function computes the proximity score between a word w and a table (identified by its name
# Each keyword of the table has a certain proximity score with w (weighted by its category according to "coef")
# We take the maximum score among all the keywords of the table
def proximity2(w,table):
    table_keywords = keywords[table]
    score = 0
    for i in range(4):
        c = coef[i]
        words = table_keywords[i]
        for x in words:
            d = max(proximity(w,x),proximity(x,w))    #as sometimes the proximity (from word_proximity) is assymetric, we resymetrize it
            score = max(score, d*c) #always take the maximum
    return score


stops = set(stopwords.words('english'))

# This function takes the sentence and return its keywords
# A token is a keyword if it is a word (only letters) and not a stopwords

def query_words(query):
    words = nltk.word_tokenize(query)
    res = []
    for w in words:
        if (is_word(w.lower()) and (w.lower() not in stops)):
            res.append(w.lower())
    return res


# This function takes a query, compute the proximity score for each table (sum of the proximity scores for each word of the query)

def tables_rank(query):
    words = query_words(query)
    n = len(words)
    res = []
    for i in range(N):
        score = 0
        table = name_list[i]
        for w in words:
            score += proximity2(w,table)
        res.append(score/n)
    return res

# This function computes the proximity score for the query with the categories (sum of the scores of each table of the category)

def cat_rank(query):
    scores = tables_rank(query)
    cat_scores = {}
    for i in range(N):
        categ = cat_list[i]
        try:
            a = cat_scores[categ]
            cat_scores[categ] = a + scores[i]
        except:
            cat_scores[categ] = scores[i]
    return cat_scores

# Pretty print of all the scores with the name of each table

def print_rank(query):
    scores = tables_rank(query)
    cat_scores = cat_rank(query)
    for i in range(len(score)):
        print(name_list[i], ' : ', scores[i])
    print()
    for a in cat_scores:
        print(a, " : ", cat_scores[a])

# Given all the scores, find the n best scores and return their values (maxs) and the corresponding ids (res)
# Works with ex-aequo scores : all the equal top scores will be returned, not just one

def find_top(score,n=1):
    res = []
    maxi = max(score)
    maxs = [maxi]
    idx = []
    for i in range(len(score)):
        if score[i] == maxi:
            idx.append(i)
    res.append(idx)
    if n>1:
        for k in range(n-1):
            m = 0
            idx = []
            for i in range(len(score)):
                if (score[i]>m and score[i]<maxi):
                    m = score[i]
            for i in range(len(score)):
                if score[i] == m:
                    idx.append(i)
            res.append(idx)
            maxi = m
            maxs.append(m)
    return (maxs,res)

# Finds the one category with the best category score

def top_category(cat_scores):
    cat = None
    m = 0
    for a in cat_scores:
        if cat_scores[a]>m:
            m = cat_scores[a]
            cat = a
    return cat

# Final function : takes a sentence as input
# And return the best scores, with the best topics associated, and also the best category

def find_topic(sent,n=3):
    scores = tables_rank(sent)
    cat_scores = cat_rank(sent)
    max_scores, topics = find_top(scores,n)
    for i in range(n):
        for k in range(len(topics[i])):
            topics[i][k] = name_list[topics[i][k]]
    top_cat = top_category(cat_scores)
    return max_scores, topics, top_cat
