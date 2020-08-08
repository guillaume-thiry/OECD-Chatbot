# This file contains all the functions that are used in the 'type of sentence' detection
# The main part of the code is the function type_of_sentence, that will be used elsewhere in the code

### IMPORT

# Utils import
from parsing_analysis import find_links, get_nodes, get_subtrees
from utils import lower_list

### FUNCTIONS

#This function determines if one of the nodes of list is a WH-word
def is_wh(nodes):
    motif = ["WHADJP", "WHADVP", "WHNP", "WHPP"]    #nodes for WH-structures
    for i in range(len(motif)):
        if motif[i] in nodes:
            return True
    return False

area_identifier = ["area", "areas", "country", "countries", "place", "places", "state", "states", "nation", "nations"]
time_identifier = ["time", "times", "year", "years"]

# The function type_of_sentence takes two parses of the sentence (the grammatical one and the dependency one) and determine the type of sentence it is
# First, it determines if the sentence is a WH-question ("WH") or a Nominal Phrase ("NP"). Other types are not supported at the moment
# Then, it determines the type of return the user wants (a value ("Value"), a list of countries ("Agr_Area") or a list of years ("Agr_Time")
# It also determines if a count is asked ("how many ...", "number of ..."), working with list of countries/years only
# Finally, if we have a list of countries or years, it means that we have detected some words like "areas" or "times"  in the sentence
# we return them with this function as well

def type_of_sentence(parse,parse_d):

    type = "NP"             #type of sentence (NP or WH)
    returned = "Value"      #return type (Value, Agr_Area, Agr_Time)
    count = None            #is a count asked (True, False)
    agg_words = []          #store the identifiers detected in the sentence

    # Determines if the sentence contains a WH-structure
    nodes = []
    for t in parse.subtrees():
        nodes.append(t.label())
    wh = is_wh(nodes)


    # The first case treated is the NP one (which is the default)
    # The reason is that you can have a WH word in a totally NP sentence ("Number of countries in |which| GDP is above ...")
    # So first we check if it is a NP, and if not, we try the WH words

    # NP Sentence

    if (parse[0].label() == "NP"):

        type = "NP"

        # We look at the tokens to see if we can find specific words (area or time identifier)
        # If we do, we look if they are connected to the word "number" like in "number of countries" to determine if there is a count or not
        tok = parse.leaves()
        b = True
        for t in tok:
            if ((t.lower() in area_identifier) and b):
                returned = "Agr_Area"
                agg_words.append(t)
                b = False
                links = lower_list(find_links(parse_d, t.lower()))
                if "number" in links:
                    count = True
            if ((t.lower() in time_identifier) and b):
                returned = "Agr_Time"
                agg_words.append(t)
                b = False
                links = lower_list(find_links(parse_d, t.lower()))
                if "number" in links:
                    count = True
        #if nothing found, the default return is a value
        if returned == None:
            returned = "Value"
        else:
            if count == None:
                count = False


    # Wh-Questions

    elif wh:
        type = "WH"

        #Capture all the possible WH-words of the sentence
        wh_words = get_nodes(parse, "WRB") + get_nodes(parse, "WP") + get_nodes(parse, "WDT")

        #Now depending on the WH-word we have, the treatment is different to get all the information
        #If multiple WH-words, we take the first one (which is the most at the beginning)
        #Example : "What are the countries where ...", we only consider "What"


        # HOW
        if (len(wh_words) > 0 and wh_words[0].lower() == "how"):

        #Generally, "how" is followed by an adjective (forming a WHADJP)
        #If so, we have to check if the adjective is "many" or "much" or something else ("how big", "how rich" ...)

            adjp = get_subtrees(parse, "WHADJP")
            if (len(adjp) == 1):    #only 1 WHADJP in the sentence (otherwise, it is complicated)
                jj = get_nodes(adjp[0], "JJ")
                if (jj != []):
                    if (('many' in jj) or ('much' in jj)):
                        # If we have a "how many" or "how much", we try to see if this is part of WHNP ("How many |something| does ...")
                        # And we try to see if the corresponding word is a area/time identifier ("how many countries", "how much time" ...)
                        try :
                            np = get_subtrees(parse, "WHNP")[0]
                            for n in np.leaves():
                                if n.lower() in area_identifier:
                                    returned = "Agr_Area"
                                    agg_words.append(n)
                                    count = True
                                elif n.lower() in time_identifier:
                                    returned = "Agr_Time"
                                    agg_words.append(n)
                                    count = True
            #else, the default will always be "Value"
                            if returned == None:
                                returned = "Value"
                        except:
                            returned = "Value"
                    else:
                        returned = "Value"
                else:
                    returned = "Value"
            else:
                returned = "Value"

        # For "What" and "Which", we try to see if a specific word is linked to that ("Which countries ...", "What are the places ...") or not ("What is the GDP of ...")

        # WHAT
        elif (len(wh_words) > 0 and wh_words[0].lower() == "what"):
            links = find_links(parse_d, "what")
            for l in links:
                if l.lower() in area_identifier:
                    returned = "Agr_Area"
                    agg_words.append(l)
                    count = False
                elif l.lower() in time_identifier:
                    returned = "Agr_Time"
                    agg_words.append(l)
                    count = False
            if returned == None:
                returned = "Value"


        # WHICH
        elif (len(wh_words) > 0 and wh_words[0].lower() == "which"):
            links = find_links(parse_d, "which")
            for l in links:
                if l.lower() in area_identifier:
                    returned = "Agr_Area"
                    agg_words.append(l)
                    count = False
                elif l.lower() in time_identifier:
                    returned = "Agr_Time"
                    agg_words.append(l)
                    count = False
            if returned == None:
                returned = "Value"

        # For the other WH-words, the meaning is directly expressed in the word ("Where" asks for a list of countries ...)

        # WHEN
        elif (len(wh_words) > 0 and wh_words[0].lower() == "when"):
            #print("WH-Questions : WHEN")
            returned = "Agr_Time"
            count = False

        # WHERE
        elif (len(wh_words) > 0 and wh_words[0].lower() == "where"):
            #print("WH-Questions : WHERE")
            returned = "Agr_Area"
            count = False

        # WHO
        elif (len(wh_words) > 0 and wh_words[0].lower() == "who"):
            #print("WH-Questions : WHO")
            returned = "Agr_Area"
            count = False






    # Yes/No Questions (not treated at the moment)

    elif (get_subtrees(parse, "SQ") != []):
        #print("Y/N Question")
        pass


    # Other sentences (order, verbal phrase...)

    # For this type of sentence, we still check if there is a area/time identifier (and a count)

    else:
        #print("Other")
        tok = parse.leaves()
        b = True
        for t in tok:
            if ((t.lower() in area_identifier) and b):
                returned = "Agr_Area"
                agg_words.append(t)
                b = False
                links = lower_list(find_links(parse_d, t.lower()))
                if "number" in links:
                    count = True
            if ((t.lower() in time_identifier) and b):
                returned = "Agr_Time"
                agg_words.append(t)
                b = False
                links = lower_list(find_links(parse_d, t.lower()))
                if "number" in links:
                    count = True

        if returned == None:
            returned = "Value"
        else:
            if count == None:
                count = False


    return (type, returned, count, agg_words)