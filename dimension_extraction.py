#  @ Copyright Inria, Ecole Polytechnique
#  Shared under the MIT license https://opensource.org/licenses/mit-license.php

# This file contains all the functions that are used in the dimension filling
# The main part of the code is the function dimension_fill, that will be used elsewhere in the code

### IMPORT

# Python libraries import
import nltk
import pickle
import pandas as pd
import os
from nltk.corpus import stopwords

# Utils import
from word_proximity import proximity
from utils import is_word, lower_list, id_max


### PATHS

path = os.getcwd()

df_path = os.path.join(path, "data/Tables.csv")
dim_path = os.path.join(path, "data/dim_dict.pkl")

### LOADINGS

df_tables = pd.read_csv(df_path, sep = ";") #DataFrame with the information of the SDMX datasets (the 12 supported right now)

# We identify each dataset by its "short name", but for the query, we need its code. We create at dictionnary for that
code = {}
for id, row in df_tables.iterrows():
    code[row["Short Name"]] = row["Code"]


# And now we create a function to have the full url to query the table

structure_prefix = "http://nsi-staging-oecd.redpelicans.com/rest/dataflow/"
structure_suffix = "?references=all&detail=referencepartial"

def get_code(name):
    try :
        c = structure_prefix + code[name] + structure_suffix
        return c
    except:
        return None

# We then load the dictionnary containing the information on the dimensions for each dataset

file = open(dim_path, "rb")
dict = pickle.load(file)
file.close()

# Stopwords (i.e not keywords)
stops = set(stopwords.words('english')) #list of common stopwords
avoid_words = ["number", "coutry", "numbers", "countries"] #other words that we want to avoid for dimension_fill

# The function dimension_fill take a table (given by table_name) and a sentence (tokens tok)
# and try to fill the dimensions of the table (i.e find a value for each dimension) with the words of the sentence


def dimension_fill(tok, table_name,seuil = 0.5):
    dim_dict = dict[table_name][0]      #dimensions and values of the table
    dim_default = dict[table_name][1]   #default value (if any) for each dimension

    final_dict = {}         #final result
    non_trivial_dim = []

    # From the tokens, we only keep the keywords, and put them in lower case
    low_tok = lower_list(tok)
    lowered_tok = []
    for t in low_tok:
        if t not in avoid_words:
            lowered_tok.append(t)

    #First, we try to see if some dimensions are trivial (only one possible valueà
    for a in dim_dict:
        if len(dim_dict[a]) == 1:
            final_dict[a] = dim_dict[a][0][0]
        else:
            non_trivial_dim.append(a)

    #For the non trivial dimensions :
    for d in non_trivial_dim:

        #We will try each value and give it a score, the value with the best score will be kept at the end
        values = dim_dict[d]
        scores = []

        for v in values:
            #we put the text of the value to the right format (tokenized, no hyphen)
            text = v[1]
            text = text.replace("-", " ")
            text_tok = nltk.word_tokenize(text)

            #and only keep relevant words (keywords)
            words = []
            for w in text_tok:
                if (w.lower() not in stops and is_word(w.lower())):
                    words.append(w.lower())

            #and then we compute the score
            n = len(words)
            s = 0
            #the score for each word of the name is the maximal proximity between this word and the words of the query
            for w in words:
                m = 0
                for t in lowered_tok:
                    pr = proximity(w, t)
                    m = max(m, pr)
                s += m
            #and we divide by the number of words in the name
            if n>0:
                s = s/n
            else:
                s = 0
            scores.append(s)
        #we take the value with the highest score, and make sure it is high enough (above a certain threshold)
        idx = id_max(scores)
        score_max = scores[idx]
        if score_max > seuil:
            final_dict[d] = dim_dict[d][idx][0]
        #else, we go for the default value
        else:
            if dim_default[d] != None:
                final_dict[d] = dim_default[d]
            else:
                final_dict[d] = None

    return final_dict
