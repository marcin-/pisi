# -*- coding: utf-8 -*-
# some helper functions for using minidom

import xml.dom.minidom as mdom

class XmlError(Exception):
    pass

# static functions

def getNodeAttribute(node, attrname):
    for i in range(node.attributes.length):
        attr = node.attributes.item(i)
        if attr.name == attrname:
            return attr.childNodes[0].data

def getNodeText(node):
    # get the first child
    try:
        child = node.childNodes[0]
    except IndexError:
        return None
    except AttributeError: # no node by that name
	return None
    if child.nodeType == child.TEXT_NODE:
        return child.data
    else:
        raise XmlError("getNodeText: Expected text node, got something else!")

def getChildText(node_s, tagpath):
    node = getNode(node_s, tagpath)
    if not node:
        return None
    return getNodeText(node)

def getChildElts(node):
    """get only child elements"""
    return filter(lambda x:x.nodeType==x.ELEMENT_NODE, node.childNodes)

def getNode(node, tagpath):
    """returns the *first* matching node for given tag path."""
    
    tags=tagpath.split('/')

    # iterative code to search for the path
        
    # get DOM for top node
    nodeList = node.getElementsByTagName(tags[0])
    if len(nodeList)==0:
        return None                 # not found

    node = nodeList[0]              # discard other matches
    for tag in tags[1:]:
        nodeList = node.getElementsByTagName(tag)
        if len(nodeList)==0:
            return None
        else:
            node = nodeList[0]

    return node

def getAllNodes(node, tags):
    """retrieve all nodes that match a given tag path."""

    if len(tags)==0:
        return []

    nodeList = node.getElementsByTagName(tags[0])
    if len(nodeList)==0:
        return []

    for tag in tags[1:]:
        results = map(lambda x: x.getElementsByTagName(tag),nodeList)
        nodeList = []
        for x in results:
            nodeList.extend(x)
            pass # emacs indentation error, keep it here

        if len(nodeList)==0:
            return []

    return nodeList


# xmlfile class that further abstracts a dom object

class XmlFile(object):
    """A class for retrieving information from an XML file"""

    def __init__(self, rootTag):
        self.rootTag = rootTag

    def readxml(self, fileName):
	self.dom = mdom.parse(fileName)

    def writexml(self, fileName):
        f = file(fileName,'w')
        self.dom.writexml(f)

    def verifyRootTag(self):
        if self.dom.documentElement.tagName != self.rootTag:
            raise XmlError("Root tagname not " % self.rootTag % " as expected")

    def getNode(self, tagPath):
	"""returns the *first* matching node for given tag path."""
        self.verifyRootTag()
        return getNode(self.dom.documentElement, tagPath)

    def getAllNodes(self, tagPath):
	"""returns all nodes matching a given tag path."""
        self.verifyRootTag()
        tags = tagPath.split('/')
        return getAllNodes(self.dom.documentElement, tags)

    def getChildren(self, tagpath):
        """ returns the children of the given path"""
        node = self.getNode(tagpath)
        return node.childNodes

    # get only elements of a given type
    # BUG: this doesn't work
    def getChildrenWithType(self, tagpath, type):
        """ returns the children of the given path, only with given type """
        node = self.getNode(tagpath)
        return filter(lambda x:x.nodeType==type, node.childNodes)

    # get only child elements
    def getChildElts(self, tagpath):
        """ returns the children of the given path, only with given type """
        node = self.getNode(tagpath)
	try:
	    return filter(lambda x:x.nodeType==x.ELEMENT_NODE, node.childNodes)
	except AttributeError:
	    return None

    def getChildText(self, tagpath):
	node = self.getNode(tagpath)
	if not node:
	    return None
	return getNodeText(node)

