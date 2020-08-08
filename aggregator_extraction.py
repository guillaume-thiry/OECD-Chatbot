# This file contains all the functions that are used in the comparison/aggregation detection
# The main part of the code is the function find_aggregators, that will be used elsewhere in the code
# The other functions are auxiliary that are being used in the main one

### IMPORT

# Python libraries import
import nltk
from nltk.parse import CoreNLPParser
from nltk.parse.corenlp import CoreNLPDependencyParser
from nltk.tag.stanford import StanfordNERTagger
import os

# Utils import
from parsing_analysis import get_nodes, get_subtrees
from utils import catch_words, cut_after, get_index

# Generic analysis functions import
from area_extraction import find_areas
from time_extraction import find_time, date_figures


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


### FUNCTIONS


# The function cut_in_clause take the whole sentence (as a list of tokens named tok)
# and the comparative words that have been detected so far (comp_words)
# and try to cut the sentence into as many clauses as there are comparative words 
# so that each clause contain one and only one comparison.
# The cuts have to be made at specific words (specified in cut_words)

cut_words = ["and", "or", "but", "while"]

def cut_in_clause(tok, comp_words,cut_words):
    res = []    #store the list of clauses
    s = []      #store the current clause
    cuts = []   #store the cut_words found
    c = False
    #We read the sentence and look for a comparative word.
    #Only once found, we look for a cut word and do the cut
    #Then, we start a new clause, looking again for a comp word and then a cut word
    for t in tok:   
        if t in comp_words:
            c = True
        if (c and t.lower() in cut_words):
            cuts.append(t.lower())
            res.append(s)
            s = []
            c = False
        else:
            s.append(t)
    if (s != []):
        res.append(s)

    return (res,cuts)


# The function get_threshold take as input a comparative word (cp_word)
# And look if the word is associated with a numerical value (a threshold)
# To do that, we look at the contextual words around cp_word to find a number
# We also make sure that the number is not already tagged as a date (in date_figures)
# Finally, we check if the number is potentially linked with a unit multiplier

unit_m = {"hundred" : 100, "hundreds" : 100, "thousand" : 1000, "thousands" : 1000,  "million" : 1000000, "millions" : 1000000, "billion" : 1000000000, "billions" : 1000000000,
"k" : 1000, 'm' : 1000000, "b" : 1000000000, "bn" : 1000000000, "bil" : 1000000000}

def get_threshold(tok,cp_word,date_figures):
    parse = next(parser.parse(tok)) #First, we parse the whole clause

    # And then we search the grammatical context of cp_word
    # This is most of the time a Prepositional Phrase (PP), a Nominal Phrase (NP) or a Quantifier Phrase (NP)
    
    pp = None
    sub = parse.subtrees()
    for s in sub:
        if (s.label() == "PP" and s.leaves()[0] == cp_word):
            pp = s
    if pp == None:
        pps = get_subtrees(parse, "PP")
        for p in pps:
            if cp_word in p.leaves():
                pp = p
    if pp == None:
        nps = get_subtrees(parse, "NP")
        for n in nps:
            if cp_word in n.leaves():
                pp = n
    if pp == None:
        qps = get_subtrees(parse, "QP")
        for q in qps:
            if cp_word in q.leaves():
                pp = q
    
    #If a context is found, we look for the first number appearing after cp_word and not being a date
    if pp != None:
        i = get_index(pp.leaves(),cp_word)  #position of the comp word in the context
        fig = get_nodes(pp, "CD")           #list of all numbers appearing in the context
        n = 0
        for f in fig:
            if (n==0 and get_index(pp.leaves(),f)>i and (f not in date_figures)):
                n=f
        
        #and if that number exists, we check if an unit multiplier is written just after
        if n != 0:
            k = get_index(tok, n) #position of the number in the clause
            mult = 1
            try:
                mult = unit_m[tok[k+1].lower()]
            except:
                pass
            return(float(n)*mult)

    return None


# The function find_aggregators takes the parses of the sentence
# and try to find every comparison and aggregation in it.
# It also takes as input the type of return the user wants (list of countries or list of years)
# and the words in the sentence giving that information

def find_aggregators(parse,parse_d,returned,agg_words):

    tok = parse.leaves()
    ner = ner_tagger.tag(tok)
    pos = pos_tagger.tag(tok)
    dep = list(dep_parser.parse(tok))[0]

    # We store the numbers in the sentence that are dates, as it is useful when looking for a threshold
    figures = date_figures(ner, pos, dep)
    
    # When a comparison or aggregation is in the sentence, the user normally wants a list of something
    # But sometimes, there is not any words specifing the type of the list and so the return is set as a value by default
    # Here, we set temporarly that return value to a list of countries
    # Thus will be useful if a comparison/aggregation is found
    # An example query for such a case would be "Highest GDPs in the world"
    if returned == "Value":
        returned = "Agr_Area"


## Comparative words

    # Some comparative words are "threshold-only" and do not require a construction with "than"
    th_words = ["over", "under", "below", "above"]
    th_inf = ["under", "below"]
    
    # We detect these words
    th_ = catch_words(tok,th_words)
    th = []

    # And just make sure that a threshold is linked to each one (as these words can appear is other contexts)
    for t in th_:
        if get_threshold(tok, t, figures) != None:
            th.append(t)
    
    
    # The other comparative words (that we will name comp words) require a structure with "than"
    # Some of them have to be specified (like "superior") but most of them are recognizied easily
    # thanks to specific tags for comparison in the POS tags
    
    cp_words = ["superior", "inferior"]
    cp_inf = ["less", "lower", "inferior", "poorer"]

    comp_ = get_nodes(parse, "RBR") + get_nodes(parse, "JJR") + catch_words(tok, cp_words)
    comp = []

    # Then, we only keep the comparative words followed by a "than"
    # And we also reorder the words at the same time, adding the threshold words in the common list

    k = 0   #determines if a comp word has already been found (used when a "than" is found)
    cp = "" #current comp word 
    for t in tok:
        if t in comp_:
            if k == 0:
                k=1
                cp = t
            if k == 1:
                cp = t
        elif t in th:
            if k == 1:  #this case happens if a threshold word is found after a comp word but before a potential than
                        #in that case, we cannot reasonably consider the comp word as it would create nested comparisons
                k = 0
                cp = ""
            comp.append(t)
        elif t == "than":
            if k == 0:
                raise Exception("Error 0 : than alone") #in case a "than" is found but without a comp word before
            elif k == 1:
                k = 0
                comp.append(cp)
                cp = ""



## Comparisons

    # Now that we have all the comparative words, we try to cut the sentence in clauses
    # Each clause must contain only one comparison (often there is just one clause)
    
    comparisons = []

    n_comp = len(comp)
    clauses, cuts = cut_in_clause(tok, comp, cut_words)

    if n_comp>0:
        if len(clauses) == n_comp:
            b = True
            for i in range(n_comp):
                if comp[i] not in clauses[i]:
                    b = False
            if not b:
                raise Exception("Error 1 : problem with clauses")

            # Else, everything is okay and we will now treat each clause separately 
            else:
                for i in range(n_comp):
                    clause = clauses[i]
                    word = comp[i]
                    
                    # We parse the clause. That way, we only consider the words of the clause and nothing else
                    # And of course, the result can differ from the parsing of the whole sentence
                    
                    clause_sent = " ".join(clause)
                    clause_parse = next(parser.parse(clause))
                    clause_dep = list(dep_parser.parse(clause))[0]
                    clause_ner = ner_tagger.tag(clause)
                    
                    # Then, we execute the functions find_areas and find_time for the clause
                    areas = find_areas(clause_sent)
                    times = find_time(clause_ner, clause_parse,clause_dep)


                    than_time = times[2]
                    to_time = times[1]
                    in_time = times[0]

                    than_area = areas[2]
                    in_area = areas[0]
                    
                    # Here, we initialize the different variables that describe a comparison
                    
                    comp_type = None    #what is the comparator (a threshold, another country/year, or something else)
                    sens = 'sup'        #is the comparison a "more than" or a "less than"
                    V1 = {}             #elements of Value1 (the first value of the comparison, before "than")
                    V2 = {}             #elements of Value2 (the second value of the comparison, after "than")
                    V = {}              #some elements are not part of the comparison and belongs to both values
                    # Example : "Countries with more population than Germany in 2010" -> we compare everything at the year 2010
                    
                    
                    # Now, we differentiate the treatment between "list of countries" and "list of years"

                    # Countries list
                    if returned == 'Agr_Area':

                        # If the comparative word is "threshold-only"
                        if word in th_words:
                            if word.lower() in th_inf:
                                sens = "inf"

                            # Search of a threshold
                            threshold = get_threshold(clause,word,[])
                            if threshold == None:
                                raise Exception("Error 2 : No threshold found")
                            else:
                                comp_type = "Threshold"
                                V2["THRESHOLD"] = threshold
                            
                            # Search of a time indicator (as we compare values, we cannot have a time series)
                            if ((in_time != None) and (in_time == to_time)):
                                V["TIME"] = in_time

                            # Search of a location indicator
                            # As the used wants a list of countries, he cannot specify a country in the query
                            # But he can give a region ("What countries in Asia ...")
                            region = True
                            r = []
                            for c in in_area:
                                if c[1] == 'country':
                                    region = False
                            if not region:
                                raise Exception("Error 3 : Country was mentioned")
                            else:
                                for c in in_area:
                                    r.append(c[0])
                            V["AREA"] = r

                        # Else, the comparative word must belong to a "than" structure
                        else:
                            if 'than' in clause:

                                if word.lower() in cp_inf:
                                    sens = "inf"

                                idx = get_index(clause, "than") #position of the "than", useful to fill V1 & V2

                                
                                # First, we look at the locations
                                # Here, it is possible to mention a country if it is the comparator

                                if len(than_area) == 1:
                                    if than_area[0][1] == "country":
                                        V2["AREA"] = than_area[0][0]
                                        comp_type = "Country"
                                    else:
                                        raise Exception("Error 4 : Comparison with a region")
                                elif len(than_area)>1:
                                    raise Exception("Error 5 : Too many area mentioned")


                                # It is also possible to mention a region, as before
                                region = True
                                r = []
                                for c in in_area:
                                    if c[1] == 'country':
                                        region = False
                                if not region:
                                    raise Exception("Error 3 : Country mentioned")
                                else:
                                    for c in in_area:
                                        r.append(c[0])
                                V["AREA"] = r


                                # Then, the time indicators
                                
                                # If two dates are found on both sides of "than", the first one go in V1 and the other in V2
                                has_than_time = False
                                if (len(than_time)==1):
                                    if in_time != None:
                                        if (get_index(clause,str(in_time)) < idx):
                                            V1["TIME"] = in_time
                                            V2["TIME"] = than_time[0]
                                            has_than_time = True
                                            if comp_type == None:
                                                comp_type = "Two"
                                
                                # Else, the year is general (goes in V)
                                if not has_than_time:
                                    if len(than_time)==1:
                                        V["TIME"] = than_time[0]
                                    elif ((in_time != None) and (in_time == to_time)):
                                        V["TIME"] = in_time
                                    else: #in case no date is given, either we raise an error or ask the user, or take a default one (to see later)
                                        #raise Exception("Error 6 : Must precise time period")
                                        pass

                                # If we haven't found yet the type of comparison, we try to find a threshold
                                # If there is not, the comparison is of type "two" (two different values compared)

                                if comp_type == None:
                                    thres = get_threshold(clause, 'than', than_time)
                                    if thres != None:
                                        comp_type = "Threshold"
                                        V2["THRESHOLD"] = thres

                                if comp_type == None:
                                    comp_type = "Two"

                            else:
                                raise Exception("Error 7 : comparison without 'than'")

                    # Years list
                    elif returned == 'Agr_Time':


                        # If threshold word
                        if word in th_words:
                            if word.lower() in th_inf:
                                sens = "inf"

                            threshold = get_threshold(clause,word,[])
                            if threshold == None:
                                raise Exception("Error 2 : No threshold found")
                            else:
                                comp_type = "Threshold"
                                V2["THRESHOLD"] = threshold

                            # As we have a list of years here, we can only have time indicators as a time period (more than one year)
                            if ((in_time != None) and (to_time != None) and (in_time != to_time)):
                                V["TIME"] = [in_time,to_time]
                            else:
                                V["TIME"] = None

                            # And conversely, the location indicators can only give one country (to be able to compare)
                            if (len(in_area) > 1 or (len(in_area) == 1 and in_area[0][1] == 'region')):
                                raise Exception("Error 5 : Too many area mentioned")
                            else:
                                if len(in_area) == 1:
                                    V["AREA"] = in_area[0][0]
                                else:
                                    V["AREA"] = None


                        # If than construction
                        else:
                            if 'than' in clause:

                                if word.lower() in cp_inf:
                                    sens = "inf"

                                idx = get_index(clause, "than")

                                # Get countries
                                
                                # We accept if two countries are given on both sides of "than" : goes in V1 & V2
                                # Else it goes in V and can only be one country
                                if len(than_area) == 1:
                                    if than_area[0][1] == "country":
                                        if (len(in_area) == 1 and in_area[0][1] == "country"):
                                            V2["AREA"] = than_area[0][0]
                                            V1["AREA"] = in_area[0][0]
                                            comp_type = "Two"
                                        elif (len(in_area) == 0):
                                            V["AREA"] = than_area[0][0]
                                        else:
                                            raise Exception("Error 5 : Too many area mentioned")
                                    else:
                                        raise Exception("Error 4 : Comparison with a region")
                                elif len(than_area)>1:
                                    raise Exception("Error 5 : Too many area mentioned")
                                elif (len(than_area) == 0):
                                    if (len(in_area) > 1 or (len(in_area) == 1 and in_area[0][1] == 'region')):
                                        raise Exception("Error 5 : Too many area mentioned")
                                    else:
                                        if len(in_area) == 1:
                                            V["AREA"] = in_area[0][0]
                                        else:
                                            V["AREA"] = None


                                # Get times
                                
                                #A specific year can be given by the user as the comparator (comp_type -> "Time")
                                if (len(than_time)==1):
                                    V2["TIME"] = than_time[0]
                                    comp_type = "Time"
                                elif(len(than_time)>1):
                                    raise Exception("Error 8 : Too many times mentioned")

                                #Else, we accept only a time period
                                if ((in_time != None) and (to_time != None) and (in_time != to_time)):
                                    V["TIME"] = [in_time,to_time]
                                else:
                                    V["TIME"] = None


                                # If nothing, we do as before and look for a threshold

                                if comp_type == None:
                                    thres = get_threshold(clause, 'than', than_time)
                                    if thres != None:
                                        comp_type = "Threshold"
                                        V2["THRESHOLD"] = thres

                                if comp_type == None:
                                    comp_type = "Two"

                            else:
                                raise Exception("Error 7 : comparison without 'than'")


                    # At the end, we gather everything for that clause and add this to the comparisons list
                    comparisons.append([comp_type,sens,V,V1,V2])

        else:
            raise Exception("Error 9 : number of words and clauses")



## Superlative words

    # Aggregation words (or superlative words) are mostly found with their specific tag
    # Nonetheless, some have to be specified
    
    sp_words = ["top", "minimum", "maximum"]
    
    sup = get_nodes(parse, "RBS") + get_nodes(parse, "JJS") + catch_words(tok, sp_words)

## Aggregations

    aggreg = None
    sens_sup = None #sense of the aggregation (max or min)
    n_sup = 1       #number of items to display
    
    sup_neg = ["least", "lowest", "worst", "minimum"]
    #we also need to know the plural form of the words that could be linked to the aggregation
    agg_plural = ["areas", "countries", "places", "states", "nations", "years"]
    
    #Sense of the aggregation
    if (sup != []):
        for s in sup:
            if s.lower() in sup_neg:
                sens_sup = 'inf'
        if sens_sup == None:
            sens_sup = 'sup'

    # For the number of items, we look at the context of the superlative words + the words linked to them
    # These words usually form a context as a Nominal Phrase (NP)
    # And in the context, we look for numerical values
    sup_ = sup + agg_words
    nps = get_subtrees(parse, "NP")
    for s in sup_:
        for np in nps:
            if s in np.leaves():
                for a in np.leaves():
                    try:
                        n_sup = int(a)
                    except:
                        pass

    # If no number was found, we look at a potential plural form
    # That would correspond to a default value of 10 items
    if n_sup == 1:
        for w in agg_words:
            if w.lower() in agg_plural:
                n_sup = 10

    if (sup != []):
        aggreg = [sens_sup,n_sup]
    
    #Finally, we return all the information found
    # 1) The list of comparison (one for each clause)
    # 2) The sense and value of the aggregation (if any)
    return(comparisons,aggreg)
