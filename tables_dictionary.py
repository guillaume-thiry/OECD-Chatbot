#  @ Copyright Inria, Ecole Polytechnique
#  Shared under the MIT license https://opensource.org/licenses/mit-license.php

# This file contains the functions used to create the metadata dictionaries for the SDMX tables supported
# A topic dictionnary contains all the information to compute the topic proximity score between a query and each table
# A dimension dictionnary contains the information to fill the dimensions of the table with the query

### IMPORT

# Python libraries import
import nltk
from nltk.corpus import stopwords
import pickle
import pandas as pd
import os

# Utils import
import utils
from metadata_extraction import *
from utils import lower_list, is_word



### PATHS

path = os.getcwd()

df_path = os.path.join(path, "data/Tables.csv")
topic_path = os.path.join(path, "data/topic_dict.pkl")
dim_path = os.path.join(path, "data/dim_dict.pkl")

### LOADINGS

region_dict = utils.region_dict
country_list = lower_list(region_dict["World"])

df_tables = pd.read_csv(df_path, sep = ";")

structure_prefix = "http://nsi-staging-oecd.redpelicans.com/rest/dataflow/"
structure_suffix = "?references=all&detail=referencepartial"

url_list = []   #list of the url (one per table)
name_list = []  #list of the table names

for id, row in df_tables.iterrows():
    name = row["Short Name"]
    code = row["Code"]
    full_code = structure_prefix + code + structure_suffix

    name_list.append(name)
    url_list.append(full_code)


## Keywords extraction for the topic score

stops = set(stopwords.words('english'))
avoid_dim = ['REPORTING_COUNTRY', 'REF_AREA', 'TIME_PERIOD', 'COUNTERPART_COUNTRY']

# This function takes as input the url of the metadata of one table
# and returns the keywords extracted from the metadata, in 4 different categories
# (Title, Description, Dimension, Category)
# There is not so much to understand here, we just go look at the keywords in the different parts of the metadata,
# keep only the relevant ones (not stopwords)
# and convert it to the right format (using codelists for example)

def keyword(url):
    # loading the xml structure as a tree
    file = urlopen(url)
    tree = ET.parse(file)
    root = tree.getroot()
    header = root[0]
    structure = root[1]

    # getting the different parts of the metadata
    concepts = get_concepts(structure)
    info = get_info(structure)
    cat = get_category(structure)
    dim = get_dimensions(structure)

    cl = get_codelists(structure)
    cons = get_constaints(structure)

    # The 4 categories
    Name = []
    Description = []
    Dimensions = []
    Category = []


    # Name keywords
    try :
        n = info["Name"]
        for w in nltk.word_tokenize(n):
            if (w.lower() not in stops and is_word(w.lower())):
                Name.append(w.lower())
    except :
        pass

    # Description keywords
    try :
        d = info["Description"]
        for w in nltk.word_tokenize(d):
            if (w.lower() not in stops and is_word(w.lower())):
                Description.append(w.lower())
    except :
        pass

    # Category keywords
    for c in cat:
        for w in nltk.word_tokenize(c):
            if (w.lower() not in stops and is_word(w.lower())):
                Category.append(w.lower())

    # Dimension keywords
    for a in dim:
        conc = concepts[dim[a][1]] #concept associated
        if (a not in avoid_dim):
            for w in nltk.word_tokenize(conc):      #words from the title of the dimension
                if (w.lower() not in stops and is_word(w.lower())):
                    Dimensions.append(w.lower())
            for c in cons[a]:                       #words from the values of the dimension
                for d in cl[dim[a][2]]:
                    if d[0] == c:
                        for w in nltk.word_tokenize(d[1]):
                            if (w.lower() not in stops and is_word(w.lower())):
                                Dimensions.append(w.lower())

    return (set(Name),set(Description),set(Dimensions),set(Category))

# Pretty print function for the 4 categories of keywords
def kprint(keyword):
    print("* Name : ", keyword[0])
    print("* Description : ", keyword[1])
    print("* Dimensions : ", keyword[2])
    print("* Category : ", keyword[3])
    print()


# Function to find the keywords for each supported table
# and save it as an independant file (topic_dict.pkl)
def topic_dict():
    d = {}
    n = len(name_list)
    for i in range(n):
        d[name_list[i]] = keyword(url_list[i])
    file = open(topic_path, "wb")
    pickle.dump(d, file)
    file.close()


## Dimensions extraction for the dimension fill

# This function takes as input the url of the metadata of one table
# and for each of its dimension, and for each value of the dimension,
# gets the words in the name of the value and store them
# These keywords are then used in dimension_fill to find the most relevant value of one given dimension

def dimension(url):

    # loading the xml structure as a tree
    file = urlopen(url)
    tree = ET.parse(file)
    root = tree.getroot()
    header = root[0]
    structure = root[1]

    # getting the different parts of the metadata
    concepts = get_concepts(structure)
    info = get_info(structure)
    dim = get_dimensions(structure)

    cl = get_codelists(structure)
    cons = get_constaints(structure)

    # For some dimension, the OECD have specified a default value (for the default display of the table)
    # This can be found in the "information" part of the metadata (see metadata_extraction)
    # So first we try to build a default dictionnary with that
    info_def = {}
    try :
        defo = info["Default"]
        for s in defo:
            t = s.split("=")
            info_def[t[0]] = t[1]
    except:
        pass

    Dimensions = {} #Words for each value for each dimension
    Default = {}    #Default value (if any) for each dimension


    for a in dim:
        if (a not in avoid_dim):    #some dimensions (like the time) are voluntarily avoided
            values = []

        #First we try to find a default value

            # If there is only one value for the dimension, it is the default
            if len(cons[a]) == 1:
                for d in cl[dim[a][2]]:
                    if d[0] == cons[a][0]:
                        Default[a] = d
            # If one value has the code '_T' (for total), it is the default
            elif ('_T' in cons[a]):
                for d in cl[dim[a][2]]:
                    if d[0] == '_T':
                        Default[a] = d
            # If the word "total" appear in the name of one value, it is the default
            else:
                def_val = None
                for c in cons[a]:
                    for d in cl[dim[a][2]]:
                        if d[0] == c:
                            if 'total' in d[1].lower():
                                def_val = d
                Default[a] = def_val

            # Else, the dimension has no default value
            if Default[a] == None:
                try :
                    for d in cl[dim[a][2]]:
                        if d[0] == info_def[a]:
                            Default[a] = d
                except:
                    pass

        #Then, for each value, we its text and add these words to the dictionnary

            for c in cons[a]:
                for d in cl[dim[a][2]]:
                    if d[0] == c:
                        values.append(d)

            Dimensions[a] = values
    return (Dimensions,Default)

# This function executes the previous one to all the supported tables
# and save it as an independant file (dim_dict.pkl)

def dim_dict():
    d = {}
    n = len(name_list)
    for i in range(n):
        d[name_list[i]] = dimension(url_list[i])
    file = open(dim_path, "wb")
    pickle.dump(d, file)
    file.close()


### Final execution

#topic_dict()
#dim_dict()
