# This file contains all the functions that are used to explore the SDMX metadata file
# These functions (to get the dimensions, the codelists...) are used elsewhere in the code when we want to interact with metadata
# (for find_topic and dimension_fill)
# This scheme should work for every extraction of OECD metadata but not necessarely with other SDMX operators

### IMPORT

# Python libraries import
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import re
from nltk.tokenize import word_tokenize

### EXAMPLE

    #URL of the metadata to explore

url_name = "http://nsi-staging-oecd.redpelicans.com/rest/dataflow/OECD.EDU/EDU_ENRLT@EAG_ENRL_SHARE_CATEGORY/1.0?references=all&detail=referencepartial"

    # Opening the xml and parsing it into a tree

file = urlopen(url_name)
tree = ET.parse(file)
root = tree.getroot()
header, structure = root

### FUNCTIONS

#Give the tag of the element :
# <Element '{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}Codelists' at 0x00000239F4A12AE8> ----> Codelists
def get_tag(a):
    tag = re.findall(r'\}\w*$',a.tag)[0]
    return tag[1:]

#Organization of the structure
# 0 : Dataflows
# 1 : CategorySchemes
# 2 : Categorisations
# 3 : Codelists
# 4 : Concepts
# 5 : DataStructures
# 6 : Constraints

# The next functions explore the xml tree looking for the useful information (constraints, codelists, concepts...)
# IMPORTANT : this is really OECD oriented and it would surely need some adjustment to handle metadata from elsewhere
# This is not so much to understand, we just go down the tree to find the information
# The best to fully understand each function is to have an overview of the SDMX metadata at the same time, to see where each function go


def get_constaints(struc):
    constraint_dict = {}
    for constraint in struc[6]:
        if (constraint.attrib['type'] == 'Actual'): #There are two constraint set, 'Actual' and 'Allowed', and we are looking for the first one
            for a in constraint:
                if (get_tag(a) == 'CubeRegion'):    #The constraint values are found in the part 'CubeRegion'
                    for key in a:
                        id = key.attrib['id']
                        if (id == 'TIME_PERIOD'):    #The syntax is special for the time period
                            time_range = [key[0][0].text,key[0][1].text]
                            constraint_dict[id] = time_range
                        else:
                            table = []
                            for b in key:
                                table.append(b.text)
                            constraint_dict[id] = table
    return constraint_dict


def get_codelists(struc):
    codelist_dict = {}
    for codelist in struc[3]:
        id = codelist.attrib['id']
        table = []
        for code in codelist:
            if (get_tag(code) == "Code"):
                key = code.attrib['id']
                for a in code:
                    if (get_tag(a) == "Name"):
                        value = a.text
                table.append((key,value))
        codelist_dict[id] = table
    return codelist_dict


def get_concepts(struc):
    concept_dict = {}
    for concept in struc[4][0]:
        if (get_tag(concept) == 'Concept'):
            id = concept.attrib['id']
            for a in concept:
                if (get_tag(a) == "Name"):
                    concept_dict[id] = a.text
    return concept_dict


def get_dimensions(struc):
    dimension_dict = {}
    for a in struc[5][0]:
        if (get_tag(a) == "DataStructureComponents"):
            for b in a:
                if (get_tag(b) == "DimensionList"):
                    for dimension in b:
                        id = dimension.attrib['id']
                        pos = dimension.attrib['position']
                        for c in dimension:
                            if (get_tag(c) == "ConceptIdentity"):
                                concept = c[0].attrib['id']
                            elif (get_tag(c) == "LocalRepresentation"):
                                if (get_tag(c[0]) == "Enumeration"):
                                    codelist = c[0][0].attrib['id']
                                else:
                                    codelist = None
                        dimension_dict[id] = (pos, concept, codelist)
    return dimension_dict


def get_attributes(struc):
    attr_dict = {}
    for a in struc[5][0]:
        if (get_tag(a) == "DataStructureComponents"):
            for b in a:
                if (get_tag(b) == "AttributeList"):
                    for attr in b:
                        id = attr.attrib['id']
                        for c in attr:
                            if (get_tag(c) == "ConceptIdentity"):
                                concept = c[0].attrib['id']
                            elif (get_tag(c) == "LocalRepresentation"):
                                if (get_tag(c[0]) == "Enumeration"):
                                    codelist = c[0][0].attrib['id']
                                else:
                                    codelist = None
                        attr_dict[id] = (concept, codelist)
    return attr_dict

#Info includes the Name (title) and the Description of the table
#it also includes default values for some dimensions (in the Annotation DEFAULT),
#useful to display a default table when loading the dataset on the webservice page
def get_info(struc):
    info_dict = {}
    for a in struc[0][0]:
        if (get_tag(a) == 'Name'):
            info_dict['Name'] = a.text
        if (get_tag(a) == 'Description'):
            info_dict['Description'] = a.text
        if (get_tag(a) == "Annotations"):
            for annot in a:
                for b in annot:
                    if (get_tag(b) == "AnnotationType" and b.text == "DEFAULT"):
                        for c in annot:
                            if (get_tag(c) == "AnnotationTitle"):
                                info_dict['Default'] = c.text.split(',')
    return info_dict

#The categories can be nested (some categories are sub-categories of other bigger categories)
#so we use a recursive auxiliary function (cat_rec) to explore that (without knowing the nesting)
def cat_rec(cat):
    res = []
    for a in cat:
        if (get_tag(a) == 'Name'):
            lang = list(a.attrib.values())[0]
            if (lang == "en"):
                res.append(a.text)
        if (get_tag(a) == 'Category'):
            r = cat_rec(a)
            res += r
    return res

def get_category(structure):
    cat_list = []
    for a in structure[1][0]:
        if (get_tag(a) == 'Category'):
            cat_list += cat_rec(a)
    return cat_list


#This function prints the different parts of the metadata we just extracted in a pretty way

def metadata(struc):
    constraints = get_constaints(struc)
    codelists = get_codelists(struc)
    concepts = get_concepts(struc)
    dimensions = get_dimensions(struc)
    attributes = get_attributes(struc)

    print("### Concepts : ", len(concepts))
    print()
    liste_key_con = list(concepts)
    for i in range(len(concepts)):
        id = liste_key_con[i]
        print (id)
    print()

    print("### Dimensions : ", len(dimensions))
    print()
    liste_key_dim = list(dimensions)
    for i in range(len(dimensions)):
        id = liste_key_dim[i]
        print (id)
    print()

    print("### Attributes : ", len(attributes))
    print()
    liste_key_attr = list(attributes)
    for i in range(len(attributes)):
        id = liste_key_attr[i]
        print (id)
    print()

    print("### Codelists : ", len(codelists))
    print()
    liste_key_cl = list(codelists)
    for i in range(len(codelists)):
        id = liste_key_cl[i]
        print (id, ' : ', len(codelists[id]), ' entries')
    print()

    print("### Constraints : ", len(constraints))
    print()
    liste_key_cstr = list(constraints)
    for i in range(len(constraints)):
        id = liste_key_cstr[i]
        print (id, ' : ', len(constraints[id]), ' entries')
    print()
