#  @ Copyright Inria, Ecole Polytechnique
#  Shared under the MIT license https://opensource.org/licenses/mit-license.php

# This files contains all the functions that are used to compute a proximity score between two words
# The main function, proximity(w,w2), is used elsewhere in the code for topic finding and dimension filling

### IMPORT

# Python libraries import
import pickle
import gensim
import nltk
from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn
import re
import pandas as pd
import os


### PATHS

path = os.getcwd()

# Word2Vec model (pretrained on GoogleNews articles)
model_path = os.path.join(path, "Google Pretrained W2V/GoogleNews-vectors-negative300.bin")
model = gensim.models.KeyedVectors.load_word2vec_format(model_path, binary=True)


### FUNCTIONS

# This function takes as input a word w
# and returns a set of words that are either hyponyms or hypernyms of w
# The relation between two words is given here by WordNet

def hyp(w,type = None):
    res = []
    for s in wn.synsets(w,type):
        for ss in s.hyponyms():
            lem = ss.lemma_names()
            for l in lem:
                res.append(l.replace("_", " "))
        for ss in s.hypernyms():
            lem = ss.lemma_names()
            for l in lem:
                res.append(l.replace("_", " "))
    return set(res)

# This function takes as input a word w
# and returns a set of words that are synonyms of w
# and another set of words that have an adjective-noun relation (partainyms) : tourism - touristic (for example)
# The relation between two words is given here by WordNet

def syn(w,type = None):
    res = []
    res2 = []
    for s in wn.synsets(w,type):
        for l in s.lemmas():
            res.append(l.name().replace("_", " "))
            per = l.pertainyms()
            rel = l.derivationally_related_forms()
            for a in per:
                res2.append(a.name().replace("_", " "))
            for a in rel:
                res2.append(a.name().replace("_", " "))

    return (set(res),set(res2))


porter = nltk.PorterStemmer()

# This function computes the proximity score between two words, combining different techniques :
# - if both words have the same stem : 1
# - synonyms : 1
# - pertainyms : 0.7
# - hypo/hypernyms : 0.6
# - else, if the word2vec similarity is above 0.2, we take that
# - else, 0

def proximity(w,w2):
    score = 0
    s = 0
    try :
        s = model.similarity(w,w2)
    except:
        pass
    if(porter.stem(w) == porter.stem(w2)):
        score = max(score,1)
    if s>0.2:
        score = max(score,s)
    hyps = hyp(w)
    syns,rels = syn(w)
    if w2 in hyps:
        score = max(score,0.6)
    if w2 in syns:
        score = max(score,1)
    if w2 in rels:
        score = max(score,0.7)
    return score
