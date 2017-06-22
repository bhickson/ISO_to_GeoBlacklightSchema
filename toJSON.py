import json, os, ogr, re
from lxml import etree as ET
from collections import OrderedDict

from xml.dom import minidom as md

#Directory where origional shapefiles/rasters exist
datadir = r"T:\SDE_Data_Preservation"
metadataDir = r"H:\geo_metadata\ArcTranslations\pythonProcessed"

isoTopicCategoriesMap = {"farming":"Farming",
                         "biota":"Biota",
                         "boundaries":"Boundaries",
                         "climatologyMeteorologyAtmosphere":"Climatology/Meteorology/Atmosphere",
                         "economy":"Economy",
                         "elevation":"Elevation",
                         "environment":"Environment",
                         "geoscientificinformation":"Geoscientific Information",
                         "health":"Health",
                         "imageryBaseMapsEarthCover":"Imagery/Base Maps/Earth Cover",
                         "intelligenceMilitary":"Intelligence/Military",
                         "inlandWaters":"Inland Waters",
                         "location":"Location",
                         "oceans":"Oceans",
                         "planningCadastre":"Planning Cadastre",
                         "society":"Society",
                         "structure":"Structure",
                         "transportation":"Transportation",
                         "utilitiesCommunications":"Utilities/Communications"}

gmd = r"http://www.isotc211.org/2005/gmd"
gml = r"http://www.opengis.net/gml"
gco = r"http://www.isotc211.org/2005/gco"
gts = r"http://www.isotc211.org/2005/gts"

ET.register_namespace("gmd", gmd)
ET.register_namespace("gml", gml)
ET.register_namespace("gco", gco)
ET.register_namespace("gts", gts)

namespaces = {'gmd':gmd,
              'gml':gml,
              'gco':gco,
              'gts':gts}

rights = "Public"           # Public or Restricted
institution = "UArizona"    # Name of holding institution
gbl_schema_version = "1.0"
layerid_prefix = "UniversityLibrary"    # Corresponds to Geoserver Workspace
isometadata_link = "https://geo.library.arizona.edu/metadata"   # Location of metadata files

filelist = {}
for root, dirs, files in os.walk(datadir):
    dirs[:] = [d for d in dirs if d not in ["ARIA"]]
    for file in files:
        if file.endswith(".shp") or file.endswith(".tif"):
            fpath = os.path.join(root, file)
            filelist[file] = fpath

def findFile(xmlFile):
    dataName = xmlFile[:-4] # Remove xml extension, should still have data extension (.tif or .shp)
    fpath = filelist[dataName]
    return(fpath)

def getDataType(file):
    datafile = findFile(file)
    if datafile:
        ext = file.split(".")[1]
        if ext == "tif":
            return(["Raster","Image"])
        elif ext == "shp":
            driver = ogr.GetDriverByName("ESRI Shapefile")
            file = driver.Open(datafile, 0)
            layer = file.GetLayer()
            sampleFeature = layer[0]
            geom = sampleFeature.GetGeometryRef().ExportToWkt().split(" ")[0]
            geomFormat = geom[0] + geom[1:].lower()
            if geomFormat == "Linestring":
                geomFormat = "Line"
            return([geomFormat, "Dataset"])
    else:
        print("Can't Find File")

def getSlugWords(file):
    wordlist = re.split("\W+|_", file)
    wordstring = ""
    for word in wordlist:
        wordstring += "-" + word.lower()
    return(wordstring)

def getSingleValue(path):
    path_string  = ""
    for i in range(0,len(path)-1):
        path_string += path[i]
        if i != len(path)-1:
            path_string += "/"
    element = root.find(path_string, namespaces)
    text = element.text

    return(text)

def getMultipleValues(path):
    values = []
    path_string = ""
    for i in range(0,len(path)-1):
        path_string += path[i]
        if i != len(path)-1:
            path_string += "/"
    elements = root.findall(path_string, namespaces)
    for element in elements:
        value = element.text
        values.append(value)
    return(values)

def getKeywordList(type):
    klist = []
    keywordTypes = root.findall("gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:type/gmd:MD_KeywordTypeCode", namespaces)
    for keywordType in keywordTypes:
        if keywordType.text == type:
            parent = keywordType.getparent().getparent()

            keywordElements = parent.findall("gmd:keyword", namespaces)
            for keywordElement in keywordElements:

                value = keywordElement.getchildren()[0].text
                if value is not None:
                    for words in value.split(","):
                        klist.append(value)

    return(list(set(klist)))

def getOrganizationName(type):
    organizationTypes = root.findall("gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode", namespaces)
    for orgType in organizationTypes:
        if orgType.text == type:
            parent = orgType.getparent().getparent()
            org_element = parent.find("gmd:organisationName", namespaces)#/gco:CharacterString", namespaces)
            char_element = org_element.find("gco:CharacterString",namespaces)#
            text = char_element.text
            return(text)




def mapIsoSubjects(list):
    for index, item in enumerate(list):
        if (item in isoTopicCategoriesMap):
            list[index] = isoTopicCategoriesMap[item]
    return(list)

def createDictionary(dict, file):
    dict["dc_identifier_s"] = getSingleValue(["gmd:dataSetURI",
                                              "gco:CharacterString"])

    dict["dc_title_s"] = getSingleValue(["gmd:identificationInfo",
                                         "gmd:MD_DataIdentification",
                                         "gmd:citation",
                                         "gmd:CI_Citation",
                                         "gmd:title",
                                         "gco:CharacterString"])

    dict["dc_description_s"] = getSingleValue(["gmd:identificationInfo",
                                               "gmd:MD_DataIdentification",
                                               "gmd:abstract",
                                               "gco:CharacterString"])

    # Point, Line, Polygon, or Raster
    dict["layer_geom_type_s"] = getDataType(file)[0]

    # Metadata Modifed date
    dict["layer_modified_dt"] = getSingleValue(["gmd:dateStamp",
                                                "gco:Date"])
    # Data format
    dict["dc_format_s"] = getSingleValue(["gmd:distributionInfo",
                                          "gmd:MD_Distribution",
                                          "gmd:distributor",
                                          "gmd:MD_Distributor",
                                          "gmd:distributorFormat",
                                          "gmd:MD_Format",
                                          "gmd:name",
                                          "gco:CharacterString"])

    # Metadata Language
    dict["dc_language_s"] = getSingleValue(["gmd:language",
                                            "gmd:LanguageCode"])

    # "Dataset" or "Image" or "PhysicalObject"
    dict["dc_type_s"] = getDataType(file)[1]


    role = getSingleValue(["gmd:identificationInfo",
                           "gmd:MD_DataIdentification",
                           "gmd:citation",
                           "gmd:CI_Citation",
                           "gmd:citedResponsibleParty",
                           "gmd:CI_ResponsibleParty",
                           "gmd:role",
                           "gmd:CI_RoleCode"])

    # Publisher Name
    # if role = publisher
    dict["dc_publisher_s"] = getOrganizationName("publisher")
    dict["dc_creator_sm"] = getOrganizationName("originator")


    # Place Names.  May need to be geonames.
    dict["dct_spatial_sm"] = getKeywordList("place")
    # A list of all subject keywords including topic Categories (topicCategory)
    descritiveKeywords = getKeywordList("theme")

    topicCategories = mapIsoSubjects(getMultipleValues(["gmd:identificationInfo",
                                                        "gmd:MD_DataIdentification",
                                                        "gmd:topicCategory",
                                                        "gmd:MD_TopicCategoryCode"]))

    keywords = descritiveKeywords + topicCategories
    # LIST OF KEYWORDS
    dict["dc_subject_sm"] = keywords

    # Date issued, Issued date for the layer, using XML Schema dateTime format (YYYY-MM-DDThh:mm:ssZ). OPTIONAL
    dict["dct_issued_s"] = getSingleValue(["gmd:identificationInfo",
                                           "gmd:MD_DataIdentification",
                                           "gmd:citation",
                                           "gmd:CI_Citation",
                                           "gmd:date",
                                           "gmd:CI_Date",
                                           "gmd:date",
                                           "gco:Date"])

    # Date or range of dates of content (years only). If range, separated by hyphen
    try:
        begDate = getSingleValue(["gmd:identificationInfo",
                                  "gmd:MD_DataIdentification",
                                  "gmd:extent",
                                  "gmd:EX_Extent",
                                  "gmd:temporalElement",
                                  "gmd:EX_TemporalExtent",
                                  "gmd:extent",
                                  "gml:TimePeriod",
                                  "gml:beginPosition"])

        endDate = getSingleValue(["gmd:identificationInfo",
                                  "gmd:MD_DataIdentification",
                                  "gmd:extent",
                                  "gmd:EX_Extent",
                                  "gmd:temporalElement",
                                  "gmd:EX_TemporalExtent",
                                  "gmd:extent",
                                  "gml:TimePeriod",
                                  "gml:endPosition"])
    except:
        endDate = getSingleValue(["gmd:identificationInfo",
                                  "gmd:MD_DataIdentification",
                                  "gmd:extent",
                                  "gmd:EX_Extent",
                                  "gmd:temporalElement",
                                  "gmd:EX_SpatialTemporalExtent",
                                  "gmd:extent",
                                  "gml:TimeInstant",
                                  "gml:timePosition"])

    wbound = getSingleValue(["gmd:identificationInfo",
                             "gmd:MD_DataIdentification",
                             "gmd:extent",
                             "gmd:EX_Extent",
                             "gmd:geographicElement",
                             "gmd:EX_GeographicBoundingBox",
                             "gmd:westBoundLongitude",
                             "gco:Decimal"])

    ebound = getSingleValue(["gmd:identificationInfo",
                             "gmd:MD_DataIdentification",
                             "gmd:extent",
                             "gmd:EX_Extent",
                             "gmd:geographicElement",
                             "gmd:EX_GeographicBoundingBox",
                             "gmd:eastBoundLongitude",
                             "gco:Decimal"])

    nbound = getSingleValue(["gmd:identificationInfo",
                             "gmd:MD_DataIdentification",
                             "gmd:extent",
                             "gmd:EX_Extent",
                             "gmd:geographicElement",
                             "gmd:EX_GeographicBoundingBox",
                             "gmd:northBoundLatitude",
                             "gco:Decimal"])

    sbound = getSingleValue(["gmd:identificationInfo",
                             "gmd:MD_DataIdentification",
                             "gmd:extent",
                             "gmd:EX_Extent",
                             "gmd:geographicElement",
                             "gmd:EX_GeographicBoundingBox",
                             "gmd:southBoundLatitude",
                             "gco:Decimal"])

    # Bounding box as maximum values for S W N E.
    # dict["georss_box_s"] = sbound + " " + wbound + " " + nbound + " " + ebound
    # Shape of the layer as a ENVELOPE WKT using W E N S.
    # dict["solr_geom"] = "ENVELOPE(" + wbound + ", " + ebound + ", " + nbound + ", " + sbound + ")"

    dict["solr_year_i"] = endDate[0:4]

    # Holding dataset for the layer, such as the name of a collection. OPTIONAL
    dict["dc_isPartOf_sm"] = ""
    # CONSTANTS
    dict["dc_rights_s"] = rights
    dict["dct_provenance_s"] = institution
    dict["geoblacklight_version"] = gbl_schema_version
    # GeoserverWorkspace:LayerName.  University of Arizona Unique
    fileName_noext = file.split(".")[0] # Removing path from file path
    dict["layer_id_s"] = layerid_prefix + ":" + fileName_noext

    # temporal (year only)
    if 'begDate' in locals():
        if begDate[:4] == endDate[:4]:
            date = endDate[0:4]
        else:
            date = begDate[0:4] + "-" + endDate[0:4]
    else:
        date = endDate

    dict["dct_temporal_sm"] = date

    dict["dct_references_s"] = OrderedDict()

    dict["dct_references_s"]["http://www.opengis.net/def/serviceType/ogc/wms"] = "https://geo.library.arizona.edu/geoserver/wms"
    dict["dct_references_s"]["http://www.opengis.net/def/serviceType/ogc/wfs"] = "https://geo.library.arizona.edu/geoserver/wfs"
        # Image viewer using Leaflet-IIIF "http://iiif.io/api/image":"",
        # Direct file download feature "http://schema.org/downloadUrl":"http://stacks.stanford.edu/file/druid:rf385pb1942/data.zip",
        # Data dictionary / documentation download "http://lccn.loc.gov/sh85035852":"",
        # Full layer description (mods link for Stanford) "http://schema.org/url":"http://purl.stanford.edu/rf385pb1942",
        # Metadata in ISO "\"http://www.isotc211.org/schemas/2005/gmd/\":"http://opengeometadata.stanford.edu/metadata/edu.stanford.purl/druid:rf385pb1942/iso19139.xml",
        # Metadata in MODS "http://www.loc.gov/mods/v3":"http://purl.stanford.edu/rf385pb1942.mods",
        # Metadata in HTML "http://www.w3.org/1999/xhtml":"http://opengeometadata.stanford.edu/metadata/edu.stanford.purl/druid:rf385pb1942/default.html",
        # ArcGIS FeatureLayer "urn:x-esri:serviceType:ArcGIS#FeatureLayer":"",
        # ArcGIS TiledMapLayer "urn:x-esri:serviceType:ArcGIS#TiledMapLayer":"",
        # ArcGIS DynamicMapLayer "urn:x-esri:serviceType:ArcGIS#DynamicMapLayer":"",
        # ArcGIS ImageMapLayer "urn:x-esri:serviceType:ArcGIS#ImageMapLayer",""

    dict["dct_references_s"]["http://www.isotc211.org/schemas/2005/gmd/"] = isometadata_link + "/" + file

    """ A slug identifies a layer in, ideally, human-readable keywords. This value
    is visible to the user and used for Permalinks. The value should be
    alpha-numeric characters separated by dashes, and is typically of the form
    institution-keyword1-keyword2. It should also be globally unique across all
    institutions in your GeoBlacklight index. Some examples of slugs include:
        india-map
        stanford-andhra-pradesh-village-boundaries
        stanford-aa111bb2222 (valid, but not ideal as it's not human-readable) """
    dict["layer_slug_s"] = institution.lower() + getSlugWords(fileName_noext)

    return(dict)

outdir = r"H:\geo_metadata\ArcTranslations\pythonProcessed\json"

for file in os.listdir(metadataDir):
    if file.endswith(".xml"):
        fpath = os.path.join(metadataDir,file)
        print("Starting", file)
        tree = ET.parse(fpath)
        root = tree.getroot()
        gblschema = OrderedDict({"dc_identifier_s": "",
                            "dc_title_s": "",
                            "dc_description_s": "",
                            "dc_rights_s": "",
                            "dct_provenance_s": "",
                            "dct_references_s": OrderedDict(),
                            "layer_id_s": "",
                            "layer_slug_s": "",
                            "layer_geom_type_s": "",
                            "layer_modified_dt": "",
                            "dc_format_s": "",
                            "dc_language_s": "",
                            "dc_type_s": "",
                            "dc_publisher_s": "",
                            "dc_creator_sm": "",
                            "dc_subject_sm": [],
                            "dct_issued_s": "",
                            "dct_temporal_sm": [],
                            "dct_spatial_sm": [],
                            "solr_geom": "",
                            "solr_year_i": "",
                            "geoblacklight_version": ""})
        builtDict = createDictionary(gblschema,file)
        outfile = outdir + "\\" + file.split(".")[0] + ".json"
        jsonString = json.dumps(builtDict, indent=4, sort_keys=False)
        with open(outfile, 'w') as jfile:
            jfile.write(jsonString)

print("FINISHED")