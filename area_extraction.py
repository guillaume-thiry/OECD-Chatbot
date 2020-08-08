# This file contains all the functions that are used in the area detection
# The main part of the code is the function find_areas, that will be used elsewhere in the code
# The other functions are auxiliary that are being used in the main one

### IMPORT

# Python libraries import
import nltk
from nltk.parse import CoreNLPParser

# Utils import
import utils
from utils import lower_list, get_index
from parsing_analysis import get_subtrees, first_word

### PARSER

parser = CoreNLPParser(url='http://localhost:9000')


### DICTIONNARIES

region_dict = utils.region_dict
demo_dict = utils.demo_dict
acro_dict = utils.acro_dict

country_list = region_dict["World"]
region_list = list(region_dict.keys())
demo_list = list(demo_dict.keys())
acro_list = list(acro_dict.keys())


### FUNCTIONS


# The function area_type takes the name of a recognized area
# and uses the dictionaires to determine if it is a region or a country

def area_type(area):
    if area in country_list:
        return 'country'
    elif area in region_list:
        return 'region'
    else:
        return None

# The function replacement replaces the abbreviated name of some countries with the complete form
# " ... UK ... " --> " ... United Kingdom ... "
# This is important as most of the abbreviations are not detected correctly by the NER

def replacement(sent):
    s = sent
    for a in acro_list:
        s = s.replace(a, acro_dict[a])
    tok = nltk.word_tokenize(s)
    return (s,tok)

def group_locations(locations, sent):
    n = len(locations)
    i = 0
    group = []
    current = ''
    while i < n:
        if current == '':
            current += locations[i]
        else:
            new = current + ' ' + locations[i]
            if new in sent:
                current = new

            else:
                group.append(current)
                current = locations[i]
        i += 1
    group.append(current)
    return group

# The function get_locations find the words in the sentence
# that are taggd as "LOCATION" by the NER

def get_locations(ner):
    res = []
    for l in ner:
        if l[1] == "LOCATION":
            res.append(l[0])
    return res

# The function bilist creates two lists of names :
# The first list contains full name of countries/regions
# while the second one contains partial name
# Therefore, "South Africa" will be in the first list and "South" in the second
# When looking at the location words in the sentence, we can easily find out if it is the name of a place
# or the beginning of the name of a place (in which case, we will go further to complete it)

def bilist(liste):
    partial = []
    for l in liste:
        words = nltk.word_tokenize(l)
        n = len(words)
        if n>1:
            i = 1
            while (i<n):
                partial.append(" ".join(words[0:i]))
                i += 1
    return (lower_list(liste),lower_list(partial))



# The function find_areas_in_list formally finds all the areas in the sentence :
# The locations identified thanks to the NER are searched in the dictionaries to make sure they exist
# Thanks to the complete and partial dictionaries (with bilist) the names in several words are detected as well
# Finally, the type of area (country or region) is also added for each location


def find_areas_in_list(tokens):
    areas = []  #final list of areas
    n = len(tokens)
    i = 0

    #First we treat the countries
    country_comp, country_part = bilist(country_list) #lists of complete and partial names of countries
    while (i<n):
        if tokens[i].lower() in country_comp:   #if the word is a complete name of country, we add it to the list
            areas.append([tokens[i], 'country', 'n'])
            i += 1
        elif tokens[i].lower() in country_part: #this works because there is no set of words being at the same time
                                                #a country and the beginning of another country (ie. in both lists)
                                                #"South" is in the partial list but not complete and vice versa for "Denmark"
            a = 1
            while(" ".join(tokens[i:i+a]).lower() in country_part):
                a += 1
            if(" ".join(tokens[i:i+a]).lower() in country_comp):
                areas.append([" ".join(tokens[i:i+a]), 'country', 'n'])
                i = i+a
            else:
                i+=1
        else:
            i += 1

    #Exactly the same, but for regions
    region_comp, region_part = bilist(region_list)
    i = 0
    while (i<n):
        if tokens[i].lower() in region_comp:
            areas.append([tokens[i], 'region', 'n'])
            i += 1
        elif tokens[i].lower() in region_part:
            a = 1
            while(" ".join(tokens[i:i+a]).lower() in region_part):
                a += 1
            if(" ".join(tokens[i:i+a]).lower() in region_comp):
                areas.append([" ".join(tokens[i:i+a]), 'region', 'n'])
                i = i+a
            else:
                i+=1
        else:
            i += 1

    #Search of the demonyms (adjectives) like "Australia" or "Russian"
    #The idea is the name (a list of complete name and another of partial names)
    #but with an extra step : when the complete adjective is found, find the name of the country/region associated
    #because we do not want adjectives but nouns in areas at the end
    #also we deal with countries and regions at the same time
    demo_comp, demo_part = bilist(demo_list)
    i = 0
    while (i<n):
        if tokens[i].lower() in demo_comp:
            name = ""
            type = ""
            for d in demo_list:
                if d.lower() == tokens[i].lower():
                    name = demo_dict[d]
            if name in country_list:
                type = "country"
            elif name in region_list:
                type = "region"
            areas.append([tokens[i], type, 'a'])
            i += 1
        elif tokens[i].lower() in demo_part:
            a = 1
            while(" ".join(tokens[i:i+a]).lower() in demo_part):
                a += 1
            if(" ".join(tokens[i:i+a]).lower() in demo_comp):
                name = ""
                type = ""
                for d in demo_list:
                    if d.lower() == " ".join(tokens[i:i+a]).lower():
                        name = demo_dict[d]
                if name in country_list:
                    type = "country"
                elif name in region_list:
                    type = "region"
                areas.append([" ".join(tokens[i:i+a]), type, 'a'])
                i = i+a
            else:
                i+=1
        else:
            i += 1

    return areas

# The function find_areas gives the final result
# Once the areas have been identified (and we know they exist) in the sentence,
# we have to look at the context to determine the role of each area (IN/FROM, TO or THAN)

# An area will be put in the category "THAN" if there is a "than" in the sentence and the area is found after it
# Indeed, sometimes a word can be a part of the comparison while being really far away from the "than"
# So we cannot just look if "than" is in the context of the word
# Example : "Countries with more male population in 2012 than the female population in 2000 in Germany"
# --> "than" may not be in the same context as "Germany" here
# So everything in that case is classified as "THAN" and a more precise analysis will be done in "find_aggregators"
# to determine if the country is or is not a real part of the comparison

# For the others, we look at the context, and more precisely, we look at the Prepositional Phrase (PP) to which the area belongs

def find_areas(sent):
    s, tok = replacement(sent)
    parse = next(parser.raw_parse(sent))
    areas = find_areas_in_list(tok)
    pps = get_subtrees(parse, "PP")
    areas_in = []
    areas_to = []
    areas_than = []


    if 'than' in tok:
        idx = get_index(tok, "than") #position of the "than"
    else:
        idx = len(tok) + 10  #if no "than", we put it after all the words (so the condition is never met)

    for a in areas:
        name = a[0] #name of the area
        type = a[1] #country or region
        form = a[2] #adjective 'a' or name 'n'
        classification = None

        if get_index(tok, name) > idx:
            classification = "THAN"
        else:
            #looking at the PP (context) of the area
            p = None
            for pp in pps:
                b = True
                for mot in name.split(" "):
                    if mot not in pp.leaves():
                        b = False
                if b:
                    p = pp.leaves()
            if p != None:

                if (('to' in p) or ('into' in p) or ('towards' in p)): #words that would indicate a category "TO"
                    classification = "TO"
                elif (('between' in p) and ('and' in p)):
                    if first_word(name, 'and', tok) == 'and':
                        classification = "TO"
                    else:
                        classification = "IN"   #most of the time, the default case is the category "IN"
                else:
                    classification = "IN"
            else:
                classification = "IN"

        #Finally, before adding the area to the list, we change its name to the good format
        #Indeed, until now, the name of the area was written as in the sentence, to find it easily
        #Now, we take the official writing, the same as in the dictionaries
        #Thus, if the word is "INDIA" or "india" or "INDia", now it becomes "India"
        name_f = []
        if form == 'a':
            for adj in demo_list:
                if adj.lower() == name.lower():
                    name_f = [demo_dict[adj],type]
        elif form == 'n':
            if type == 'country':
                for c in country_list:
                    if c.lower() == name.lower():
                        name_f = [c,type]
            elif type == 'region':
                for r in region_list:
                    if r.lower() == name.lower():
                        name_f = [r,type]

        if classification == "IN":
            areas_in.append(name_f)
        elif classification == "TO":
            areas_to.append(name_f)
        elif classification == "THAN":
            areas_than.append(name_f)

    return (areas_in,areas_to,areas_than)

# Pretty print of the areas found, with their attributes

def areas_print(areas_classified):
    print("IN AREAS :    ", areas_classified[0])
    print("TO AREAS :    ", areas_classified[1])
    print("THAN AREAS :  ", areas_classified[2])






