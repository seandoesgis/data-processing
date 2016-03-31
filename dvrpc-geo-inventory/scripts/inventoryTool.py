"""
This script looks through all folders in a directory to find .sde files
and extract the metadata and data information providing an output
that is easily consumed by excel or js. This serves as a mechanism for 
exrtacting a DVRPC data directory for staff to explore currently available
geographic data.

The output is two CSV files: 
    1- Full data table directory
    2- Full listing of fields for all tables

Only SDE database connections are supported, not folder workspaces.

Parameters:
    0 - Output/save directory

***********************************************
Limitations: Currently limited to ArcGIS Toolbox due to decoding error 
in Windows environment.
**********************************************

Written by: Michael Ruane, DVRPC
Date updated: 10/26/2015
"""

import arcpy
import os
import sys
import csv
import tempfile
import codecs
import cStringIO
import re, htmlentitydefs
from HTMLParser import HTMLParser
from xml.etree.ElementTree import ElementTree

def ListWorkspaceContentsAndMetadata(workspace):
    """Generator function that lists the contents of the geodatabase including those within feature datasets.
       Certain metadata elements are also listed. Only geodatabases are supported, not folder workspaces."""

    if not arcpy.Exists(workspace):
        raise ValueError("Workspace %s does not exist!" % workspace)

    desc = arcpy.Describe(workspace)
    if desc.dataType == 'FeatureDataset':
        validationWorkspace = os.path.dirname(workspace)
        fdsName = arcpy.ParseTableName(desc.name, validationWorkspace).split(",")[2].strip() # Get the short name of the feature dataset (sans database/owner name)
    else:
        validationWorkspace = workspace
        fdsName = ""

    if not desc.dataType in ['Workspace', 'FeatureDataset']:
        if not hasattr(desc, "workspaceType") or not desc.workspaceType in ["LocalDatabase", "RemoteDatabase"]:
            raise ValueError("Workspace %s is not a geodatabase!" % workspace)

    children = desc.children
    if desc.dataType == 'FeatureDataset':
        validationWorkspace = os.path.dirname(workspace)
        fdsName = arcpy.ParseTableName(desc.name, validationWorkspace).split(",")[2].strip() # Get the short name of the feature dataset (sans database/owner name)
    else:
        validationWorkspace = workspace
        fdsName = ""

    for child in children:
        # Parse the full table name into database, owner, table name
        database, owner, tableName = [i.strip() if i.strip() != "(null)" else "" for i in arcpy.ParseTableName(child.name, validationWorkspace).split(",")]
        datasetType = child.datasetType if hasattr(child, "datasetType") else ""
        dataShape = child.shapeType if hasattr(child, "shapeType") else ""

        if datasetType == 'FeatureClass' or datasetType == 'Table' : 
            dtype = dataShape if datasetType == 'FeatureClass' else datasetType
            outrow = [xstr(owner), xstr(tableName), xstr(fdsName), xstr(dtype)]
            try:
                outrow.extend(GetMetadataItems(child.catalogPath))
            except:
                pass
            print ",".join(outrow)
            yield outrow

        # Recurse to get the contents of feature datasets
        if datasetType == 'FeatureDataset':
            for outrow in ListWorkspaceContentsAndMetadata(child.catalogPath):
                yield outrow

def ListWorkspaceFieldContentsAndMetadata(workspace):
    """Generator function that lists the contents of the geodatabase including those within feature datasets.
       Certain metadata elements are also listed. Only geodatabases are supported, not folder workspaces."""

    if not arcpy.Exists(workspace):
        raise ValueError("Workspace %s does not exist!" % workspace)

    desc = arcpy.Describe(workspace)
    if desc.dataType == 'FeatureDataset':
        validationWorkspace = os.path.dirname(workspace)
        fdsName = arcpy.ParseTableName(desc.name, validationWorkspace).split(",")[2].strip() # Get the short name of the feature dataset (sans database/owner name)
    else:
        validationWorkspace = workspace
        fdsName = ""

    if not desc.dataType in ['Workspace', 'FeatureDataset']:
        if not hasattr(desc, "workspaceType") or not desc.workspaceType in ["LocalDatabase", "RemoteDatabase"]:
            raise ValueError("Workspace %s is not a geodatabase!" % workspace)

    children = desc.children
    if desc.dataType == 'FeatureDataset':
        validationWorkspace = os.path.dirname(workspace)
        fdsName = arcpy.ParseTableName(desc.name, validationWorkspace).split(",")[2].strip() # Get the short name of the feature dataset (sans database/owner name)
    else:
        validationWorkspace = workspace
        fdsName = ""

    for child in children:
        # Parse the full table name into database, owner, table name
        database, owner, tableName = [i.strip() if i.strip() != "(null)" else "" for i in arcpy.ParseTableName(child.name, validationWorkspace).split(",")]
        datasetType = child.datasetType if hasattr(child, "datasetType") else ""
        dataShape = child.shapeType if hasattr(child, "shapeType") else ""

        if datasetType == 'FeatureClass' or datasetType == 'Table' : 
            dtype = dataShape if datasetType == 'FeatureClass' else 'Table'
            fieldrow = [xstr(owner), xstr(tableName), xstr(dtype)]
            try:
                fieldList = GetFieldMetaItems(child.catalogPath)
                itemizedFields = fieldList.split('!,! ')
                c = (len(itemizedFields))-3
                
                h = 1
                for i in xrange(0,c,4):
                    aFields = [itemizedFields[i],itemizedFields[i+1],itemizedFields[i+2],itemizedFields[i+3]]
                    #i += 4
                    newrow = fieldrow + aFields
                    yield newrow    
            except:
                pass
            #print ",".join(outrow)
            #yield outrow

        # Recurse to get the contents of feature datasets
        if datasetType == 'FeatureDataset':
            for newrow in ListWorkspaceFieldContentsAndMetadata(child.catalogPath):
                yield newrow

def CreateCSVFile(csvfile, header):
    """Creates a CSV file from the input header and row sequences"""
    with open(csvfile, 'wb') as f:
        f.write(codecs.BOM_UTF8) # Write Byte Order Mark character so Excel knows this is a UTF-8 file
        w = UnicodeWriter(f, dialect='excel', encoding='utf-8')
        if header:
            w.writerow(header)
            
def WriteCSVFile(csvfile, rows):
    """Creates a CSV file from the input header and row sequences"""
    with open(csvfile, 'ab') as f:
        f.write(codecs.BOM_UTF8) # Write Byte Order Mark character so Excel knows this is a UTF-8 file
        w = UnicodeWriter(f, dialect='excel', encoding='utf-8')
        w.writerows(rows)

def CreateHeaderRow():
    """Specifies the column names (header row) for the CSV file"""
    return ("OWNER", "TABLE_NAME", "FEATURE_DATATSET", "DATASET_TYPE", "NAME", "CONTACT_PER", "ABSTRACT", "PURPOSE", "USE_LIMIT", "SEARCH_KEYS", "MOD_DATE", "ITEM_COUNT")

def CreateFieldHeaderRow():
    """Specifies the column names (header row) for the CSV file"""
    return ("OWNER", "TABLE", "DATA_TYPE", "LABEL", "ALIAS", "TYPE", "DESC")

def CreateDummyXMLFile():
    """Creates an XML file with the required root element 'metadata' in
    the user's temporary files directory. Returns the path to the file.
    The calling code is responsible for deleting the temporary file."""
    tempdir = tempfile.gettempdir()
    fd, filepath = tempfile.mkstemp(".xml", text=True)
    with os.fdopen(fd, "w") as f:
        f.write("<metadata />")
        f.close()
    return filepath

def GetMetadataElementTree(dataset):
    """Creates and returns an ElementTree object from the specified
    dataset's metadata"""
    xmlfile = CreateDummyXMLFile()
    arcpy.MetadataImporter_conversion(dataset, xmlfile)
    tree = ElementTree()
    tree.parse(xmlfile)
    os.remove(xmlfile)
    return tree

def GetElementText(tree, elementPath):
    """Returns the specified element's text if it exists or an empty
    string if not."""
    element = tree.find(elementPath)
    return element.text if element != None else "No variable"

def GetFirstElementText(tree, elementPaths):
    """Returns the first found element matching one of the specified
    element paths"""
    result = ""
    for elementPath in elementPaths:
        element = tree.find(elementPath)
        if element != None:
            result = element.text
            break
    return result

def ListElementsText(tree, elementPath):
    """Returns a comma+space-separated list of the text values of all
    instances of the specified element, or an empty string if none are
    found."""
    elements = tree.findall(elementPath)
    if elements:
        return ", ".join([element.text for element in elements])
    else:
        return ""
def ListAttrDescElementsText(tree, elementPath):
    """Returns a comma+space-separated list of the text values of all
    instances of the specified element, or an empty string if none are
    found."""
    elements = tree.findall("eainfo/detailed/attr")  
    if elements:
        return ", ".join([GetElementText(element, elementPath) for element in elements])
    else:
        return ""

def GetFieldAttrs(tree, elementPath):
    elements = tree.findall(elementPath) 
    if elements:
        return "!,! ".join([(GetElementText(element, "attrlabl")+"!,! "+GetElementText(element, "attalias")+"!,! "+ GetElementText(element, "attrtype")+"!,! "+GetElementText(element, "attrdef")) for element in elements])
    else:
        return ""


def GetMetadataItems(dataset):
    """Retrieves certain metadata text elements from the specified dataset"""
    tree = GetMetadataElementTree(dataset)
    featurename = GetElementText(tree, "dataIdInfo/idCitation/resTitle") # Originator
    pocorg = GetFirstElementText(tree, ("idinfo/ptcontac/cntinfo/cntperp/cntper", # Point of contact organization (person primary contact)
                                        "idinfo/ptcontac/cntinfo/cntorgp/cntper")) # Point of contact organization (organization primary contact)
    abstract = strip_tags(unescape(GetElementText(tree, "dataIdInfo/idAbs"))) # Abstract
    purpose = strip_tags(unescape(GetElementText(tree, "dataIdInfo/idPurp"))) # Purpose
    useLimit = strip_tags(unescape(GetElementText(tree, "dataIdInfo/resConst/Consts/useLimit"))) # Purpose
    searchkeys = ListElementsText(tree, "idinfo/keywords/theme/themekey") #ListElementsText(tree, "dataIdInfo/searchKeys/keyword") # Search keywords
    modDate = GetElementText(tree, "mdDateSt") # Theme keywords
    itemCount = GetElementText(tree, "eainfo/detailed/enttyp/enttypc")
    del tree
    metadataItems = (xstr(featurename), xstr(pocorg), xstr(abstract), xstr(purpose), xstr(useLimit), xstr(searchkeys), xstr(modDate), xstr(itemCount))
    return metadataItems

def GetFieldMetaItems(dataset):
    """Retrieves certain metadata text elements from the specified dataset"""
    tree = GetMetadataElementTree(dataset)
    field_attrs = GetFieldAttrs(tree, "eainfo/detailed/attr")
    del tree
    return field_attrs

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def xstr(s):
    if s is None:
        return ''
    else:
        return str(s)

if __name__ == '__main__':
    #rootdir = r"V:\Transportation"
    saveLocation = arcpy.GetParameterAsText(0)
    #saveLocation = r"D:\dvrpc_shared\FY2016\VOutput"
    csvFile = saveLocation+"\dvrpc_geo_inventory.csv"
    csvFieldFile = saveLocation+"\dvrpc_field_inventory.csv"
    headerRow = CreateHeaderRow()
    fieldHeaderRow = CreateFieldHeaderRow()
    #print headerRow
    CreateCSVFile(csvFile, headerRow)
    CreateCSVFile(csvFieldFile, fieldHeaderRow)
    rootdir = os.path.dirname("V:/")
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            if file.endswith(".sde"):
                workspace = os.path.join(subdir, file)
                #print workspace
                datasetRows = ListWorkspaceContentsAndMetadata(workspace)
                WriteCSVFile(csvFile, datasetRows)
                fieldRows = ListWorkspaceFieldContentsAndMetadata(workspace)
                WriteCSVFile(csvFieldFile, fieldRows)