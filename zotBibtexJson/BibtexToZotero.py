"""
Some functions to map bibtex to zotero json, in order to interract with zotero api.
Functions are mostly inspired from

official bibtex translator of zotero:
https://github.com/zotero/translators/blob/master/BibTeX.js

and bibtexparser:
https://github.com/sciunto-org/python-bibtexparser

"""

__author__= "Kaan Eraslan"
__license__= "MIT License, see LICENSE"

import re
import uuid

def bibtex_text_read(bibDatabase_str):
    """
    params: bibDatabase_str, str.
    return: bibTeXREF_list, []
    """
    #
    bib_element_re = re.compile("@.+?(?=@)", re.S)
    bibTeXREF_list = re.findall(bib_element_re, bibDatabase_str)
    #
    return bibTeXREF_list


def bibtex_type_map(bibtex_dict, zotero_dict):
    """
    params: bibtex_dict, dict.
    return: zotero_dict, dict.
    """
    #
    if bibtex_dict["type"] == "inproceedings":
        zotero_dict["itemType"] = "conferencePaper"
    elif bibtex_dict["type"] == "book":
        zotero_dict["itemType"] = "book"
    elif bibtex_dict["type"] == "article":
        zotero_dict["itemType"] = "journalArticle"
    elif bibtex_dict["type"] == "inbook":
        zotero_dict["itemType"] = "bookSection"
    elif bibtex_dict["type"] == "incollection":
        zotero_dict["itemType"] = "bookSection"
    elif bibtex_dict["type"] == "patent":
        zotero_dict["itemType"] = "patent"
    elif bibtex_dict["type"] == "phdthesis":
        zotero_dict["itemType"] = "thesis"
    elif bibtex_dict["type"] == "unpublished":
        zotero_dict["itemType"] = "manuscript"
    elif bibtex_dict["type"] == "conference":
        zotero_dict["itemType"] = "conferencePaper"
    elif bibtex_dict["type"] == "techreport":
        zotero_dict["itemType"] = "report"
    elif bibtex_dict["type"] == "booklet":
        zotero_dict["itemType"] = "book"
    elif bibtex_dict["type"] == "manual":
        zotero_dict["itemType"] = "book"
    elif bibtex_dict["type"] == "mastersthesis":
        zotero_dict["itemType"] = "thesis"
    elif bibtex_dict["type"] == "misc":
        zotero_dict["itemType"] = "book"
    elif bibtex_dict["type"] == "proceedings":
        zotero_dict["itemType"] = "book"
    elif bibtex_dict["type"] == "online":
        zotero_dict["itemType"] = "webpage"
    #
    return zotero_dict

def bibtex_field_map(bibtex_dict, zotero_dict, bibtex_type):
    """
    params: bibtex_dict, dict.
    return: zotero_dict, dict.
    """
    #
    if "comments" in bibtex_dict.keys():
        zotero_dict["notes"] = bibtex_dict["comments"]
    if "annote" in bibtex_dict.keys():
        zotero_dict["notes"] = bibtex_dict["annote"]
    if "review" in bibtex_dict.keys():
        zotero_dict["notes"] = bibtex_dict["review"]
    if "notes" in bibtex_dict.keys():
        zotero_dict["notes"] = bibtex_dict["notes"]
    if "keywords" in bibtex_dict.keys():
        zotero_dict["tags"] = bibtex_dict["keywords"]
    if "keyword" in bibtex_dict.keys():
        zotero_dict["tags"] = bibtex_dict["keyword"]
    if "date" in bibtex_dict.keys():
        zotero_dict["date"] = bibtex_dict["date"]
    if "pages" in bibtex_dict.keys() and (bibtex_type == "book" or bibtex_type == "thesis" or bibtex_type == "manuscript"):
        zotero_dict["numPages"] = bibtex_dict["pages"]
    if "pages" in bibtex_dict.keys() and bibtex_type != "book" and bibtex_type != "thesis" and bibtex_type != "manuscript":
        zotero_dict["pages"] = bibtex_dict["pages"]
    if "year" in bibtex_dict.keys():
        zotero_dict["date"] = bibtex_dict["year"]
    if "title" in bibtex_dict.keys():
        zotero_dict["title"] = bibtex_dict["title"]
    if "lastchecked" in bibtex_dict.keys():
        zotero_dict["accessDate"] = bibtex_dict["lastchecked"]
    if "urldate" in bibtex_dict.keys():
        zotero_dict["accessDate"] = bibtex_dict["urldate"]
    if "journal" in bibtex_dict.keys():
        zotero_dict["publicationTitle"] = bibtex_dict["journal"]
    if "number" in bibtex_dict.keys() and bibtex_type == "report":
        zotero_dict["reportNumber"] = bibtex_dict["number"]
    if "number" in bibtex_dict.keys() and (bibtex_type == "book" or bibtex_type == "bookSection" or bibtex_type == "conferencePaper"):
        zotero_dict["seriesNumber"] = bibtex_dict["number"]
    if "number" in bibtex_dict.keys() and bibtex_type == "patent":
        zotero_dict["patentNumber"] = bibtex_type["number"]
    if "booktitle" in bibtex_dict.keys():
        zotero_dict["publicationTitle"] = bibtex_dict["booktitle"]
    if "school" in bibtex_dict.keys():
        zotero_dict["publisher"] = bibtex_dict["school"]
    if "institution" in bibtex_dict.keys():
        zotero_dict["publisher"] = bibtex_dict["institution"]
    if "issue" in bibtex_dict.keys():
        zotero_dict["issue"] = bibtex_dict["issue"]
    if "location" in bibtex_dict.keys():
        zotero_dict["place"] = bibtex_dict["location"]
    if "address" in bibtex_dict.keys():
        zotero_dict["place"] = bibtex_dict["address"]
    if "chapter" in bibtex_dict.keys():
        zotero_dict["section"] = bibtex_dict["chapter"]
    if "edition" in bibtex_dict.keys():
        zotero_dict["edition"] = bibtex_dict["edition"]
    if "series" in bibtex_dict.keys():
        zotero_dict["series"] = bibtex_dict["series"]
    if "volume" in bibtex_dict.keys():
        zotero_dict["volume"] = bibtex_dict["volume"]
    if "copyright" in bibtex_dict.keys():
        zotero_dict["rights"] = bibtex_dict["copyright"]
    if "isbn" in bibtex_dict.keys():
        zotero_dict["ISBN"] = bibtex_dict["isbn"]
    if "issn" in bibtex_dict.keys():
        zotero_dict["ISSN"] = bibtex_dict["issn"]
    if "shorttitle" in bibtex_dict.keys():
        zotero_dict["shortTitle"] = bibtex_dict["shorttitle"]
    if "url" in bibtex_dict.keys():
        zotero_dict["url"] = bibtex_dict["url"]
    if "doi" in bibtex_dict.keys():
        zotero_dict["DOI"] = bibtex_dict["doi"]
    if "abstract" in bibtex_dict.keys():
        zotero_dict["abstractNote"] = bibtex_dict["abstract"]
    if "nationality" in bibtex_dict.keys():
        zotero_dict["country"] = bibtex_dict["nationality"]
    if "language" in bibtex_dict.keys():
        zotero_dict["language"] = bibtex_dict["language"]
    if "assignee" in bibtex_dict.keys():
        zotero_dict["assignee"] = bibtex_dict["assignee"]
    #
    return zotero_dict


def bibtex_parse_name(bibtex_dict, zotero_dict):
    """
    params:
    bibtex_dict, {}
    zotero_dict, {}

    return: zotero_dict, {}

    """
    #
    names_list = []
    #
    if "author" in bibtex_dict.keys():
        names_list.append(
            ("author", bibtex_dict["author"])
        )
    if "editor" in bibtex_dict.keys():
        names_list.append(
            ("editor", bibtex_dict["editor"])
        )
    if "translator" in bibtex_dict.keys():
        names_list.append(
            ("translator", bibtex_dict["translator"])
        )
    #
    creators = []
    for names_value in names_list:
        names_divided = names_value[1].strip().split(" and ")
        for i in range(len(names_divided)):
            creator = {}
            if len(names_divided[i]) == 0:
                continue
            elif len(names_divided[i]) > 0:
                name_divide = names_divided[i].split(",")
                if len(name_divide) > 1:
                    creator["firstName"] = name_divide.pop()
                    creator["lastName"] = name_divide.pop(0)
                    if len(name_divide) > 0:
                        creator["firstName"] = creator["firstName"] + ", ".join(name_divide)
                    creator["creatorType"] = names_value[0]
            creators.append(creator)
    zotero_dict["creators"] = creators
    #
    return zotero_dict

def bibtexTozotero(bibtex_dict, zotero_dict):
    """
    params:
    bibtex_dict, {}
    zotero_dict, {}

    return: bibtex_names, {}
    """
    #
    bibtex_type = bibtex_type_map(bibtex_dict, zotero_dict)
    bibtex_fields = bibtex_field_map(bibtex_dict, bibtex_type, bibtex_type["itemType"])
    bibtex_names = bibtex_parse_name(bibtex_dict, bibtex_fields)
    #
    return bibtex_names

def bibtexNoteszotero(bibtex_names):
    """
    params:
    bibtex_names, {}
    response, {}

    return: notes_dict, {}
    """
    #
    notes_dict = {}
    notes_dict["itemType"] = "note"
    notes_dict["relations"] = {}
    notes_dict["tags"] = []
    notes_dict["note"] = bibtex_names["notes"].strip()
    #
    return notes_dict

def zotero_collection_map(zotero_item_list, collection=""):
    """
    params:
    zotero_item_list, [{},{},...]
    collection, str.

    return: zotero_collection_list, []
    """
    #
    zotero_collection_list = []
    #
    for zotero_item in zotero_item_list:
        zotero_item["collections"] = []
        zotero_item["collections"].append(collection)
        zotero_collection_list.append(zotero_item)
    #
    return zotero_collection_list

def zotero_write_token():
    """
    str.
    """
    #
    token = str(uuid.uuid4().hex)
    #
    return token
