#  @ Copyright Inria, Ecole Polytechnique
#  Shared under the MIT license https://opensource.org/licenses/mit-license.php

#This files contains all the utils functions used to explore the parsing trees
#In particular, these functions allows us to easily extract information from the grammatical structure tree and the dependency tree


# This function takes as input grammatical structure tree and the name of a node (like "NN", "VB" or "JJ")
# and return all the words in the sentence under this node
# A tree height of 2 means that the tree has a tag as its root and the leaf under it is directly a word of the sentence (last layer)
def get_nodes(tree, node):
    if tree.label() == node:
        return tree.leaves()
    else:
        res = []
        if tree.height() > 2:
            for t in tree:
                res += get_nodes(t, node)
        return res

# This function is almost the same as the last one but return trees (not just the leaves) corresponding to the given nodes
# For example, it is possible to ask for all the PPs of the sentence, and they will return as subtrees
# If a tree with the right node (for example "NP") contains subtrees with also this node, the function will recursively explore those
# And so return the lowest NPs possible
def get_subtrees(tree, node):
    if tree.label() == node:
        if tree.height() > 2:
            b = False
            for a in tree:
                if a.label() == node:
                    b = True
            if b:
                res = []
                for t in tree:
                    res += get_subtrees(t, node)
                return res
            else:
                return [tree]
        else:
            return [tree]
    else:
        res = []
        if tree.height() > 2:
            for t in tree:
                res += get_subtrees(t, node)
        return res


# This function works with the dependency tree and returns all the words having a link in the tree with the word given in input
# Links are given as triples : (word_1, link_type, word_2)
def find_links(parse_d, word):
    res = []
    for a,b,c in parse_d.triples():
        if (a[0].lower() == word):
            res.append(c[0])
        elif (c[0].lower() == word):
            res.append(a[0])
    return res

# This function is given a list of tokens and two words appearing in it and return the first one
# useful to see the order of two words in the sentence
def first_word(w1,w2,tokens):
    m1 = w1.split(' ')[0]   #We only need to find the first word (if case the name is in multiple part)
    m2 = w2.split(' ')[0]
    for t in tokens:
        if t==m1:           #w1 found first
            return w1
        if t==m2:           #w2 found first
            return w2
