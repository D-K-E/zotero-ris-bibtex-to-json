# Zotero RIS to JSON Data Python Translator: -------------------

original_creators = "Simon Kornblith and Aurimas Vinckevicius"

# For list of contributors, see: https://github.com/zotero/translators/blob/master/RIS.js

__author__ = "Kaan Eraslan"

"""
General Structure of the Algorithm:
Parse the RIS
Transform RIS to Python Dict
Request Template from the Zotero server depending on the
itemType given by the Python Dict
Cache the empty template to a file for later use.
Map python dict data to template
Divide the total number of data to a list of 50 items
Upload the lists one after another in a series of requests:

POST <userOrGroupPrefix>/items # Request method
Content-Type: application/json # Header Variable
Zotero-Write-Token: <write token> # Header Variable?
"""

# Packages ----------------------------------------------

import requests
import re
import os
import uuid

# --------------------------------------------------------

type_map = {
    "ADVS":"film",
    "AGGR":"document", #how can we handle "database" citations?
    "ANCIENT":"document",
    "BILL":"bill",
    "BLOG":"blogPost",
    "BOOK":"book",
    "CHAP":"bookSection",
    "CHART":"artwork",
    "CLSWK":"book",
    "COMP":"computerProgram",
    "CONF":"conferencePaper",
    "CPAPER":"conferencePaper",
    "CTLG":"magazineArticle",
    "DATA":"document", #dataset
    "DBASE":"document", #database
    "DICT":"dictionaryEntry",
    "EBOOK":"book",
    "ECHAP":"bookSection",
    "EDBOOK":"book",
    "EJOUR":"journalArticle",
    "ENCYC":"encyclopediaArticle",
    "EQUA":"document", # what's a good way to handle this?
    "FIGURE":"artwork",
    "GEN":"journalArticle",
    "GOVDOC":"report",
    "GRNT":"document",
    "HEAR":"hearing",
    "ICOMM":"email",
    "INPR":"manuscript",
    "JFULL":"journalArticle",
    "JOUR":"journalArticle",
    "LEGAL":"case", #is this what they mean?
    "MANSCPT":"manuscript",
    "MAP":"map",
    "MGZN":"magazineArticle",
    "MPCT":"film",
    "MULTI":"videoRecording", # maybe?
    "MUSIC":"audioRecording",
    "NEWS":"newspaperArticle",
    "PAMP":"manuscript",
    "PAT":"patent",
    "PCOMM":"letter",
    "RPRT":"report",
    "SER":"book",
    "SLIDE":"presentation",
    "SOUND":"audioRecording", # consider MUSIC
    "STAND":"report",
    "STAT":"statute",
    "THES":"thesis",
    "UNBILL":"manuscript",
    "UNPD":"manuscript",
    "VIDEO":"videoRecording",
    "CASE":"case",
    "ABST":"journalArticle",
    "ART":"artwork",
    "BOOK":"book",
    "ELEC":"webpage",
    "WEB":"webpage"	# not in spec, but used by EndNote
}

field_map = {
    "AB":"abstractNote",
    "AN":"archiveLocation",
    "CN":"callNumber",
    "DB":"archive",
    "DO":"DOI",
    "DP":"libraryCatalog",
    "J2":"journalAbbreviation",
    "KW":"tags",
    "L1":"attachments/PDF",
    "L2":"attachments/HTML",
    "L4":"attachments/other",
    "N1":"notes",
    "ST":"shortTitle",
    "UR":"url",
    "Y2":"accessDate",
    "CA": "unsupported/Caption",
    "CR": "rights",
    "CT": "title",
    "ED": "creators/editor",
    "EP": "pages",
    #	"H1": "unsupported/Library Catalog", # Citavi specific (possibly multiple occurences)
    "H1":"libraryCatalog",
    "H2":"callNumber",
    #	"H2": "unsupported/Call Number", # Citavi specific (possibly multiple occurences)
    "JA": "journalAbbreviation",
    "JF": "publicationTitle",
    "LB":"label",
    "M2": "extra", # not in spec
    "N2": "abstractNote",
    "RN": "notes"
}

# type specific
	# tag => field:itemTypes
	# if itemType not explicitly given, __default field is used
    # unless itemType is excluded in exclude

dependent_fields = {
    "TI": {
		"__default":"title",
		"subject":["email"],
		"caseName":["case"],
		"nameOfAct":["statute"]
	},
	"T2": {
		"code":["bill", "statute"],
		"bookTitle":["bookSection"],
		"blogTitle":["blogPost"],
		"conferenceName":["conferencePaper"],
		"dictionaryTitle":["dictionaryEntry"],
		"encyclopediaTitle":["encyclopediaArticle"],
		"committee":["hearing"],
		"forumTitle":["forumPost"],
		"websiteTitle":["webpage"],
		"programTitle":["radioBroadcast", "tvBroadcast"],
		"meetingName":["presentation"],
		"seriesTitle":["computerProgram", "map", "report"],
		"series": ["book"],
		"publicationTitle":["journalArticle", "magazineArticle", "newspaperArticle"],
        "__default":"backupPublicationTitle"
	},
    "TA": "unsupported/Translated Author",
    "TT": "unsupported/Translated Title",
	"T3": {
		"legislativeBody":["hearing", "bill"],
		"series":["bookSection", "conferencePaper", "journalArticle","book"],
		"seriesTitle":["audioRecording"]
	},
	# NOT "HANDLED": reviewedAuthor, scriptwriter, contributor, guest
	"AU": {
		"__default":"creators/author",
		"creators/artist":["artwork"],
		"creators/cartographer":["map"],
		"creators/composer":["audioRecording"],
		"creators/director":["film", "radioBroadcast", "tvBroadcast", "videoRecording"], # this clashes with audioRecording
		"creators/interviewee":["interview"],
		"creators/inventor":["patent"],
		"creators/podcaster":["podcast"],
		"creators/programmer":["computerProgram"]
	},
	"A2": {
		"creators/sponsor":["bill"],
		"creators/performer":["audioRecording"],
		"creators/presenter":["presentation"],
		"creators/interviewer":["interview"],
		"creators/editor":["journalArticle", "bookSection", "conferencePaper", "dictionaryEntry", "document", "encyclopediaArticle"],
		"creators/seriesEditor":["book", "report"],
		"creators/recipient":["email", "instantMessage", "letter"],
		"reporter":["case"],
		"issuingAuthority":["patent"]
	},
	"A3": {
		"creators/cosponsor":["bill"],
		"creators/producer":["film", "tvBroadcast", "videoRecording", "radioBroadcast"],
		"creators/editor":["book"],
		"creators/seriesEditor":["bookSection", "conferencePaper", "dictionaryEntry", "encyclopediaArticle", "map"]
	},
	"A4": {
		"__default":"creators/translator",
		"creators/counsel":["case"],
		"creators/contributor":["conferencePaper", "film"]	# translator does not fit these
	},
	"C1": {
		"filingDate":["patent"], # not in spec
		"creators/castMember":["radioBroadcast", "tvBroadcast", "videoRecording"],
		"scale":["map"],
		"place":["conferencePaper"]
	},
	"C2": {
		"issueDate":["patent"], # not in spec
		"creators/bookAuthor":["bookSection"],
		"creators/commenter":["blogPost"]
	},
	"C3": {
		"artworkSize":["artwork"],
		"proceedingsTitle":["conferencePaper"],
		"country":["patent"]
	},
	"C4": {
		"creators/wordsBy":["audioRecording"], # not in spec
		"creators/attorneyAgent":["patent"],
		"genre":["film"]
	},
	"C5": {
		"references":["patent"],
		"audioRecordingFormat":["audioRecording", "radioBroadcast"],
		"videoRecordingFormat":["film", "tvBroadcast", "videoRecording"]
	},
	"C6": {
		"legalStatus":["patent"],
	},
	"CY": {
		"__default":"place",
		"__exclude":["conferencePaper"] # should be exported as C1
        # if conferencePaper then CY -> C1, restart
	},
	"DA": { # also see PY when editing
		"__default":"date",
		"dateEnacted":["statute"],
		"dateDecided":["case"],
		"issueDate":["patent"]
	},
	"ET": {
		"__default":"edition",
 		"__ignore":["journalArticle"], # EPubDate. If journalArticle, pop or delete ET.
		"session":["bill", "hearing", "statute"],
		"version":["computerProgram"]
	},
	"IS": {
		"__default":"issue",
		"numberOfVolumes": ["bookSection"]
	},
	"LA": {
		"__default":"language",
		"programmingLanguage": ["computerProgram"]
	},
	"M1": {
		"seriesNumber":["book"],
		"billNumber":["bill"],
		"system":["computerProgram"],
		"documentNumber":["hearing"],
		"applicationNumber":["patent"],
		"publicLawNumber":["statute"],
		"episodeNumber":["podcast", "radioBroadcast", "tvBroadcast"],
        "__default":"extra",
		"issue": ["journalArticle"], # EndNote hack
		"numberOfVolumes": ["bookSection"],	# EndNote exports here instead of IS
		"accessDate": ["webpage"]		# this is access date when coming from EndNote
	},
	"M3": {
		"manuscriptType":["manuscript"],
		"mapType":["map"],
		"reportType":["report"],
		"thesisType":["thesis"],
		"websiteType":["blogPost", "webpage"],
		"postType":["forumPost"],
		"letterType":["letter"],
		"interviewMedium":["interview"],
		"presentationType":["presentation"],
		"artworkMedium":["artwork"],
		"audioFileType":["podcast"],
        "__default":"DOI"
	},
	"NV": {
		"__default": "numberOfVolumes",
		"__exclude": ["bookSection"] # IS. If bookSection then NV -> IS, restart
	},
	"OP": {
		"history":["hearing", "statute", "bill", "case"],
		"priorityNumbers":["patent"],
#        "__default": "unsupported/Original Publication",
#		"unsupported/Content": ["blogPost", "computerProgram", "film", "presentation", "report", "videoRecording", "webpage"]
	},
	"PB": {
		"__default":"publisher",
		"label":["audioRecording"],
		"court":["case"],
		"distributor":["film"],
		"assignee":["patent"],
		"institution":["report"],
		"university":["thesis"],
		"company":["computerProgram"],
		"studio":["videoRecording"],
		"network":["radioBroadcast", "tvBroadcast"]
	},
	"PY": { # duplicate of DA, but this will only output year
		"__default":"date",
		"dateEnacted":["statute"],
		"dateDecided":["case"],
		"issueDate":["patent"]
	},
	"SE": {
		"__default": "section",	# though this can refer to pages, start page, etc. for some types. Zotero does not support any of those combinations, however.
		"__exclude": ["case"] # if case then pop/delete SE.
#		"unsupported/File Date": ["case"]
	},
	"SN": {
		"__default":"ISBN",
		"ISSN":["journalArticle", "magazineArticle", "newspaperArticle"],
		"patentNumber":["patent"],
		"reportNumber":["report"],
	},
	"SP": {
		"__default":"pages", # needs extra processing
		"codePages":["bill"], # bill
		"numPages":["book", "thesis", "manuscript"], # manuscript not really in spec
		"firstPage":["case"],
		"runningTime":["film"]
	},
	"SV": {
		"seriesNumber": ["bookSection"],
		"docketNumber": ["case"]	# not in spec. EndNote exports this way
	},
	"VL": {
		"__default":"volume",
		"codeNumber":["statute"],
		"codeVolume":["bill"],
		"reporterVolume":["case"],
		"__exclude":["patent"], # if patent or webpage then pop/delete VL.
        #"unsupported/Patent Version Number":['patent'],
		"accessDate": ["webpage"]	# technically access year according to EndNote
	},
    "AD": {
		"__default": "unsupported/Author Address",
		"unsupported/Inventor Address": ["patent"]
	},
    "AV": "archiveLocation", # REFMAN
    "BT": {
		"title": ["book", "manuscript"],
		"bookTitle": ["bookSection"],
		"__default": "backupPublicationTitle" # we do more filtering on this later
	},
	"ID": "__ignore", # No support ? If Id pop/delete ID
	"JO": {
		"__default": "journalAbbreviation",
		"conferenceName": ["conferencePaper"]
	},
#	"LB": "unsupported/Label",
	"RI": {
		"__default":"unsupported/Reviewed Item",
		"unsupported/Article Number": ["statute"]
	},
	"T1": "TI", # if T1 then TI, restart.
    "Y1": "DA", #  Old RIS spec. if Y1 then DA, restart
    "RP": "ET", # We map Reprint Edition to Edition
    "A1": "AU" # if A1 then AU, restart
}

# non-standard or degenerate field maps
# used ONLY for importing and only if these fields are not specified above (e.g. M3)
# these are not exported the same way


non_standard_field_maps= {
#	"A1": "AU", # if A1 then AU, restart
#	"AD": {
#		"__default": "unsupported/Author Address",
#		"unsupported/Inventor Address": ["patent"]
#	},
#	"AV": "archiveLocation", # REFMAN
#	"BT": {
#		"title": ["book", "manuscript"],
#		"bookTitle": ["bookSection"],
#		"__default": "backupPublicationTitle" # we do more filtering on this later
#	},
#	"CA": "unsupported/Caption",
#    "CR": "rights",
#	"CT": "title",
#	"ED": "creators/editor",
#	"EP": "pages",
#	"H1": "unsupported/Library Catalog", # Citavi specific (possibly multiple occurences)
#	"H2": "unsupported/Call Number", # Citavi specific (possibly multiple occurences)
#	"ID": "__ignore", # No support ? If Id pop/delete ID
#	"JA": "journalAbbreviation",
#	"JF": "publicationTitle",
#	"JO": {
#		"__default": "journalAbbreviation",
#		"conferenceName": ["conferencePaper"]
#	},
#	"LB": "unsupported/Label",
#	"M1": {
#		"__default":"extra",
#		"issue": ["journalArticle"], # EndNote hack
#		"numberOfVolumes": ["bookSection"],	# EndNote exports here instead of IS
#		"accessDate": ["webpage"]		# this is access date when coming from EndNote
#	},
#	"M2": "extra", # not in spec
#	"M3": "DOI",
#	"N2": "abstractNote",
#	"NV": "numberOfVolumes",
#	"OP": {
#		"__default": "unsupported/Original Publication",
#		"unsupported/Content": ["blogPost", "computerProgram", "film", "presentation", "report", "videoRecording", "webpage"]
#	},
#	"RI": {
#		"__default":"unsupported/Reviewed Item",
#		"unsupported/Article Number": ["statute"]
#	},
#	"RN": "notes",
#	"SE": {
#		"unsupported/File Date": ["case"]
#	},
#	"T1": "TI", # if T1 then TI, restart.
#	"T2": "backupPublicationTitle", # most item types should be covered above
#	"T3": {
#		"series": ["book"]
#	},
#	"TA": "unsupported/Translated Author",
#   "TT": "unsupported/Translated Title",
#	"VL": {
#		"unsupported/Patent Version Number":['patent'],
#		"accessDate": ["webpage"]	# technically access year according to EndNote
#	},
#	"Y1": "DA" #  Old RIS spec. if Y1 then DA, restart
}

# Test Text --------------------------------------------------------

test_input_1 = """TY  - JOUR\nA1  - Baldwin,S.A.\nA1  - Fugaccia,I.\nA1  - Brown,D.R.\nA1  - Brown,L.V.\nA1  - Scheff,S.W.\nT1  - Blood-brain barrier breach following\ncortical contusion in the rat\nJO  - J.Neurosurg.\nY1  - 1996\nVL  - 85\nSP  - 476\nEP  - 481\nRP  - Not In File\nKW  - cortical contusion\nKW  - blood-brain barrier\nKW  - horseradish peroxidase\nKW  - head trauma\nKW  - hippocampus\nKW  - rat\nN2  - Adult Fisher 344 rats were subjected to a unilateral impact to the dorsal cortex above the hippocampus at 3.5 m/sec with a 2 mm cortical depression. This caused severe cortical damage and neuronal loss in hippocampus subfields CA1, CA3 and hilus. Breakdown of the blood-brain barrier (BBB) was assessed by injecting the protein horseradish peroxidase (HRP) 5 minutes prior to or at various times following injury (5 minutes, 1, 2, 6, 12 hours, 1, 2, 5, and 10 days). Animals were killed 1 hour after HRP injection and brain sections were reacted with diaminobenzidine to visualize extravascular accumulation of the protein. Maximum staining occurred in animals injected with HRP 5 minutes prior to or 5 minutes after cortical contusion. Staining at these time points was observed in the ipsilateral hippocampus. Some modest staining occurred in the dorsal contralateral cortex near the superior sagittal sinus. Cortical HRP stain gradually decreased at increasing time intervals postinjury. By 10 days, no HRP stain was observed in any area of the brain. In the ipsilateral hippocampus, HRP stain was absent by 3 hours postinjury and remained so at the 6- and 12- hour time points. Surprisingly, HRP stain was again observed in the ipsilateral hippocampus 1 and 2 days following cortical contusion, indicating a biphasic opening of the BBB following head trauma and a possible second wave of secondary brain damage days after the contusion injury. These data indicate regions not initially destroyed by cortical impact, but evidencing BBB breach, may be accessible to neurotrophic factors administered intravenously both immediately and days after brain trauma.\nER  - """

test_input_2 = """TY  - PAT\nA1  - Burger,D.R.\nA1  - Goldstein,A.S.\nT1  - Method of detecting AIDS virus infection\nY1  - 1990/2/27\nVL  - 877609\nIS  - 4,904,581\nRP  - Not In File\nA2  - Epitope,I.\nCY  - OR\nPB  - 4,629,783\nKW  - AIDS\nKW  - virus\nKW  - infection\nKW  - antigens\nY2  - 1986/6/23\nM1  - G01N 33/569 G01N 33/577\nM2  - 435/5 424/3 424/7.1 435/7 435/29 435/32 435/70.21 435/240.27 435/172.2 530/387 530/808 530/809 935/110\nN2  - A method is disclosed for detecting the presence of HTLV III infected cells in a medium. The method comprises contacting the medium with monoclonal antibodies against an antigen produced as a result of the infection and detecting the binding of the antibodies to the antigen. The antigen may be a gene product of the HTLV III virus or may be bound to such gene product. On the other hand the antigen may not be a viral gene product but may be produced as a result of the infection and may further be bound to a lymphocyte. The medium may be a human body fluid or a culture medium. A particular embodiment of the present method involves a method for determining the presence of a AIDS virus in a person. The method comprises combining a sample of a body fluid from the person with a monoclonal antibody that binds to an antigen produced as a result of the infection and detecting the binding of the monoclonal antibody to the antigen. The presence of the binding indicates the presence of a AIDS virus infection. Also disclosed are novel monoclonal antibodies, noval compositions of matter, and novel diagnostic kits\nER  - """

test_input_3 = """TY  - AGGR\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nCA  - Caption\nCY  - Place Published\nDA  - Date Accessed\nDB  - Name of Database\nDO  - 10.1234/123456\nDP  - Database Provider\nET  - Date Published\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Publication Number\nM3  - Type of Work\nN1  - Notes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRN  - ResearchNotes\nSE  - Screens\nSN  - ISSN/ISBN\nSP  - Pages\nST  - Short Title\nT2  - Periodical\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nID  - 2\nER  - \n\n\nTY  - ANCIENT\nA2  - Editor\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nCN  - Call Number\nCA  - Caption\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Abbreviated Publication\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Text Number\nM3  - Type of Work\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - ResearchNotes\nRP  - Reprint Edition\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Publication Title\nT3  - Volume Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 3\nER  - \n\n\nTY  - ART\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Artist\nC3  - Size/Length\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDP  - Database Provider\nDO  - DOI\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Size\nM3  - Type of Work\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSP  - Description\nST  - Short Title\nTI  - Title\nTT  - Translated Title\nTA  - Author, Translated\nUR  - URL\nY2  - Access Date\nID  - 4\nER  - \n\n\nTY  - ADVS\nA2  - Performers\nA3  - Editor, Series\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Cast\nC2  - Credits\nC3  - Size/Length\nC5  - Format\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number\nM3  - Type\nN1  - Notes\nNV  - Extent of Work\nOP  - Contents\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSN  - ISBN\nST  - Short Title\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 5\nER  - \n\n\nTY  - BILL\nA2  - Sponsor\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nCA  - Caption\nCN  - Call Number\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Session\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nN1  - Notes\nM1  - Bill Number\nOP  - History\nPY  - Year\nRN  - Research Notes\nSE  - Code Section\nSP  - Code Pages\nST  - Short Title\nT2  - Code\nT3  - Legislative Body\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Code Volume\nY2  - Access Date\nID  - 6\nER  - \n\n\nTY  - BLOG\nA2  - Editor\nA3  - Illustrator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Author Affiliation\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Last Update Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM3  - Type of Medium\nN1  - Notes\nOP  - Contents\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSE  - Message Number\nSN  - ISBN\nSP  - Description\nST  - Short Title\nT2  - Title of WebLog\nT3  - Institution\nTA  - Author, Translated\nTI  - Title of Entry\nTT  - Translated Title\nUR  - URL\nVL  - Access Year\nY2  - Number\nID  - 7\nER  - \n\n\nTY  - BOOK\nA2  - Editor, Series\nA3  - Editor\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC3  - Title Prefix\nC4  - Reviewer\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Series Volume\nM3  - Type of Work\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Pages\nSN  - ISBN\nSP  - Number of Pages\nST  - Short Title\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 8\nER  - \n\n\nTY  - CHAP\nA2  - Editor\nA3  - Editor, Series\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Section\nC3  - Title Prefix\nC4  - Reviewer\nC5  - Packaging Method\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number of Volumes\nOP  - Original Publication\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Chapter\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nSV  - Series Volume\nT2  - Book Title\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 9\nER  - \n\n\nTY  - CASE\nA2  - Reporter\nA3  - Court, Higher\nA4  - Counsel\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nCA  - Caption\nCN  - Call Number\nDA  - Date Accessed\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Action of Higher Court\nJ2  - Parallel Citation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM3  - Citation of Reversal\nN1  - Notes\nNV  - Reporter Abbreviation\nOP  - History\nPB  - Court\nPY  - Year Decided\nRN  - ResearchNotes\nSE  - Filed Date\nSP  - First Page\nST  - Abbreviated Case Name\nSV  - Docket Number\nT3  - Decision\nTA  - Author, Translated\nTI  - Case Name\nTT  - Translated Title\nUR  - URL\nVL  - Reporter Volume\nID  - 10\nER  - \n\n\nTY  - CTLG\nA2  - Institution\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC5  - Packaging Method\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Series Volume\nM3  - Type of Work\nN1  - Notes\nNV  - Catalog Number\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Number of Pages\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 11\nER  - \n\n\nTY  - CHART\nA2  - File, Name of\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - By, Created\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Version\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number\nM3  - Type of Image\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSP  - Description\nT2  - Image Source Program\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Image Size\nY2  - Access Date\nID  - 12\nER  - \n\n\nTY  - CLSWK\nA2  - Editor, Series\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Attribution\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Series Volume\nM3  - Type\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nRP  - Reprint Edition\nSN  - ISSN/ISBN\nSP  - Number of Pages\nST  - Short Title\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 23\nER  - \n\n\nTY  - COMP\nA2  - Editor, Series\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Programmer\nC1  - Computer\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Version\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM3  - Type\nN1  - Notes\nOP  - Contents\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSN  - ISBN\nSP  - Description\nST  - Short Title\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Edition\nY2  - Access Date\nID  - 14\nER  - \n\n\nTY  - CPAPER\nA2  - Editor\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Place Published\nCA  - Caption\nCY  - Conference Location\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Issue\nM3  - Type\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSP  - Pages\nT2  - Conference Name\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 15\nER  - \n\n\nTY  - CONF\nA2  - Editor\nA3  - Editor, Series\nA4  - Sponsor\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Place Published\nC2  - Year Published\nC3  - Proceedings Title\nC5  - Packaging Method\nCA  - Caption\nCN  - Call Number\nCY  - Conference Location\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Issue\nN1  - Notes\nNV  - Number of Volumes\nOP  - Source\nPB  - Publisher\nPY  - Year of Conference\nRN  - Research Notes\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Conference Name\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 16\nER  - \n\n\nTY  - DATA\nA2  - Producer\nA4  - Agency, Funding\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Investigators\nC1  - Time Period\nC2  - Unit of Observation\nC3  - Data Type\nC4  - Dataset(s)\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date of Collection\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Version\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nN1  - Notes\nNV  - Study Number\nOP  - Version History\nPB  - Distributor\nPY  - Year\nRI  - Geographic Coverage\nRN  - Research Notes\nSE  - Original Release Date\nSN  - ISSN\nST  - Short Title\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nY2  - Access Date\nID  - 17\nER  - \n\n\nTY  - DICT\nA2  - Editor\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Term\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number\nM3  - Type of Work\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Version\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Dictionary Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 13\nER  - \n\n\nTY  - EDBOOK\nA2  - Editor, Series\nA4  - Translator\nAB  - Abstract\nAD  - Editor Address\nAN  - Accession Number\nAU  - Editor\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Series Volume\nM3  - Type of Work\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nRP  - Reprint Edition\nSN  - ISBN\nSP  - Number of Pages\nST  - Short Title\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 19\nER  - \n\n\nTY  - EJOUR\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Year Cited\nC2  - Date Cited\nC3  - PMCID\nC4  - Reviewer\nC5  - Issue Title\nC6  - NIHMSID\nC7  - Article Number\nCA  - Caption\nCY  - Place Published\nDA  - Date Accessed\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Issue\nM3  - Type of Work\nN1  - Notes\nNV  - Document Number\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - E-Pub Date\nSN  - ISSN\nSP  - Pages\nST  - Short Title\nT2  - Periodical Title\nT3  - Website Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nID  - 20\nER  - \n\n\nTY  - EBOOK\nA2  - Editor\nA3  - Editor, Series\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Year Cited\nC2  - Date Cited\nC3  - Title Prefix\nC4  - Reviewer\nC5  - Last Update Date\nC6  - NIHMSID\nC7  - PMCID\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date Accessed\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM3  - Type of Medium\nN1  - Notes\nNV  - Version\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSN  - ISBN\nSP  - Number of Pages\nT2  - Secondary Title\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nID  - 21\nER  - \n\n\nTY  - ECHAP\nA2  - Editor\nA3  - Editor, Series\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Section\nC3  - Title Prefix\nC4  - Reviewer\nC5  - Packaging Method\nC6  - NIHMSID\nC7  - PMCID\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Series Volume\nM3  - Type of Work\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSN  - ISSN/ISBN\nSP  - Number of Pages\nST  - Short Title\nT2  - Book Title\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 22\nER  - \n\n\nTY  - ENCYC\nA2  - Editor\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Term\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Encyclopedia Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 18\nER  - \n\n\nTY  - EQUA\nA2  - File, Name of\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - By, Created\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Version\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number\nM3  - Type of Image\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSP  - Description\nT2  - Image Source Program\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Image Size\nY2  - Access Date\nID  - 24\nER  - \n\n\nTY  - FIGURE\nA2  - File, Name of\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - By, Created\nCN  - Call Number\nCA  - Caption\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Version\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number\nM3  - Type of Image\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSP  - Description\nT2  - Image Source Program\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Image Size\nY2  - Access Date\nID  - 25\nER  - \n\n\nTY  - MPCT\nA2  - Director, Series\nA3  - Producer\nA4  - Performers\nAB  - Synopsis\nAD  - Author Address\nAN  - Accession Number\nAU  - Director\nC1  - Cast\nC2  - Credits\nC4  - Genre\nC5  - Format\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date Released\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM3  - Medium\nN1  - Notes\nPB  - Distributor\nPY  - Year Released\nRN  - Research Notes\nRP  - Reprint Edition\nSP  - Running Time\nST  - Short Title\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nY2  - Access Date\nID  - 26\nER  - \n\n\nTY  - GEN\nA2  - Author, Secondary\nA3  - Author, Tertiary\nA4  - Author, Subsidiary\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Custom 1\nC2  - Custom 2\nC3  - Custom 3\nC4  - Custom 4\nC5  - Custom 5\nC6  - Custom 6\nC7  - Custom 7\nC8  - Custom 8\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number\nM3  - Type of Work\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Section\nSN  - ISSN/ISBN\nSP  - Pages\nST  - Short Title\nT2  - Secondary Title\nT3  - Tertiary Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 27\nER  - \n\n\nTY  - GOVDOC\nA2  - Department\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Government Body\nC2  - Congress Number\nC3  - Congress Session\nCA  - Caption\nCY  - Place Published\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSE  - Section\nSN  - ISSN/ISBN\nSP  - Pages\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 28\nER  - \n\n\nTY  - GRANT\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Investigators\nC1  - Contact Name\nC2  - Contact Address\nC3  - Contact Phone\nC4  - Contact Fax\nC5  - Funding Number\nC6  - CFDA Number\nCA  - Caption\nCN  - Call Number\nCY  - Activity Location\nDA  - Deadline\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Requirements\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Status\nM3  - Funding Type\nN1  - Notes\nNV  - Amount Received\nOP  - Original Grant Number\nPB  - Sponsoring Agency\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Review Date\nSE  - Duration of Grant\nSP  - Pages\nST  - Short Title\nTA  - Author, Translated\nTI  - Title of Grant\nTT  - Translated Title\nUR  - URL\nVL  - Amount Requested\nY2  - Access Date\nID  - 29\nER  - \n\n\nTY  - HEAR\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nC2  - Congress Number\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Session\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Document Number\nN1  - Notes\nNV  - Number of Volumes\nOP  - History\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Committee\nT3  - Legislative Body\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nY2  - Access Date\nID  - 30\nER  - \n\n\nTY  - JOUR\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Legal Note\nC2  - PMCID\nC6  - NIHMSID\nC7  - Article Number\nCA  - Caption\nCN  - Call Number\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Epub Date\nJ2  - Periodical Title\nLA  - Language\nLB  - Label\nIS  - Issue\nM3  - Type of Article\nOP  - Original Publication\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Start Page\nSN  - ISSN\nSP  - Pages\nST  - Short Title\nT2  - Journal\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 31\nER  - \n\n\nTY  - LEGAL\nA2  - Organization, Issuing\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date of Code Edition\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Start Page\nM3  - Type of Work\nN1  - Notes\nNV  - Session Number\nOP  - History\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSE  - Section Number\nSN  - ISSN/ISBN\nSP  - Pages\nT2  - Title Number\nT3  - Supplement No.\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Rule Number\nY2  - Access Date\nID  - 32\nER  - \n\n\nTY  - MGZN\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Issue Number\nM3  - Type of Article\nN1  - Notes\nNV  - Frequency\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Start Page\nSN  - ISSN\nSP  - Pages\nST  - Short Title\nT2  - Magazine\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 33\nER  - \n\n\nTY  - MANSCPT\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Description of Material\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Folio Number\nM3  - Type of Work\nN1  - Notes\nNV  - Manuscript Number\nPB  - Library/Archive\nPY  - Year\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Start Page\nSP  - Pages\nST  - Short Title\nT2  - Collection Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume/Storage Container\nY2  - Access Date\nID  - 34\nER  - \n\n\nTY  - MAP\nA2  - Editor, Series\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Cartographer\nC1  - Scale\nC2  - Area\nC3  - Size\nC5  - Packaging Method\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM3  - Type\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nRP  - Reprint Edition\nSN  - ISSN/ISBN\nSP  - Description\nST  - Short Title\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nY2  - Access Date\nID  - 35\nER  - \n\n\nTY  - MUSIC\nA2  - Editor\nA3  - Editor, Series\nA4  - Producer\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Composer\nC1  - Format of Music\nC2  - Form of Composition\nC3  - Music Parts\nC4  - Target Audience\nC5  - Accompanying Matter\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM3  - Form of Item\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Section\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Album Title\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 36\nER  - \n\n\nTY  - NEWS\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Reporter\nC1  - Column\nC2  - Issue\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Issue Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  -  Edition\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Start Page\nM3  - Type of Article\nN1  - Notes\nNV  - Frequency\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Section\nSN  - ISSN\nSP  - Pages\nST  - Short Title\nT2  - Newspaper\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 37\nER  - \n\n\nTY  - DBASE\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nCA  - Caption\nCY  - Place Published\nDA  - Date Accessed\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Date Published\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM3  - Type of Work\nN1  - Notes\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSN  - Report Number\nSP  - Pages\nT2  - Periodical\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nID  - 38\nER  - \n\n\nTY  - MULTI\nA2  - Editor, Series\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - By, Created\nC1  - Year Cited\nC2  - Date Cited\nC5  - Format/Length\nCA  - Caption\nDA  - Date Accessed\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number of Screens\nM3  - Type of Work\nN1  - Notes\nPB  - Distributor\nPY  - Year\nRN  - Research Notes\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nID  - 39\nER  - \n\n\nTY  - PAMP\nA2  - Institution\nA4  - Translator\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC5  - Packaging Method\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Series Volume\nM3  - Type of Work\nN1  - Notes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nRP  - Reprint Edition\nM2  - Number of Pages\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Published Source\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Number\nY2  - Access Date\nID  - 40\nER  - \n\n\nTY  - PAT\nA2  - Organization, Issuing\nA3  - International Author\nAB  - Abstract\nAD  - Inventor Address\nAN  - Accession Number\nAU  - Inventor\nC2  - Issue Date\nC3  - Designated States\nC4  - Attorney/Agent\nC5  - References\nC6  - Legal Status\nCA  - Caption\nCN  - Call Number\nCY  - Country\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - International Patent Classification\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Application Number\nM3  - Patent Type\nN1  - Notes\nNV  - US Patent Classification\nOP  - Priority Numbers\nPB  - Assignee\nPY  - Year\nRN  - Research Notes\nSE  - International Patent Number\nSN  - Patent Number\nSP  - Pages\nST  - Short Title\nT2  - Published Source\nT3  - Title, International\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Patent Version Number\nY2  - Access Date\nID  - 41\nER  - \n\n\nTY  - PCOMM\nA2  - Recipient\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Senders E-Mail\nC2  - Recipients E-Mail\nCN  - Call Number\nCA  - Caption\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Description\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Folio Number\nM3  - Type\nN1  - Notes\nNV  - Communication Number\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSP  - Pages\nST  - Short Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nY2  - Access Date\nID  - 42\nER  - \n\n\nTY  - RPRT\nA2  - Editor, Series\nA3  - Publisher\nA4  - Department/Division\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC6  - Issue\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Document Number\nM3  - Type\nN1  - Notes\nNV  - Series Volume\nOP  - Contents\nPB  - Institution\nPY  - Year\nRN  - Research Notes\nRP  - Notes\nSN  - Report Number\nSP  - Pages\nST  - Short Title\nTA  - Author, Translated\nT2  - Series Title\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 43\nER  - \n\n\nTY  - SER\nA2  - Editor\nA3  - Editor, Series\nA4  - Editor, Volume\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Section\nC2  - Report Number\nC5  - Packaging Method\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Series Volume\nM3  - Type of Work\nN1  - Notes\nNV  - Number of Volumes\nOP  - Original Publication\nPB  - Publisher\nPY  - Year\nRI  - Reviewed Item\nRN  - Research Notes\nRP  - Reprint Edition\nSE  - Chapter\nSN  - ISBN\nSP  - Pages\nST  - Short Title\nT2  - Secondary Title\nT3  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Volume\nY2  - Access Date\nID  - 44\nER  - \n\n\nTY  - STAND\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Institution\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Start Page\nM3  - Type of Work\nN1  - Notes\nNV  - Session Number\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSE  - Section Number\nSN  - Document Number\nSP  - Pages\nT2  - Section Title\nT3  - Paper Number\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Rule Number\nY2  - Access Date\nID  - 45\nER  - \n\n\nTY  - STAT\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nC5  - Publisher\nC6  - Volume\nCA  - Caption\nCN  - Call Number\nCY  - Country\nDA  - Date Enacted\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Session\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Public Law Number\nN1  - Notes\nNV  - Statute Number\nOP  - History\nPB  - Source\nPY  - Year\nRI  - Article Number\nRN  - Research Notes\nSE  - Sections\nSP  - Pages\nST  - Short Title\nT2  - Code\nT3  - International Source\nTA  - Author, Translated\nTI  - Name of Act\nTT  - Translated Title\nUR  - URL\nVL  - Code Number\nY2  - Access Date\nID  - 46\nER  - \n\n\nTY  - THES\nA3  - Advisor\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Document Number\nM3  - Thesis Type\nN1  - Notes\nPB  - University\nPY  - Year\nRN  - Research Notes\nSP  - Number of Pages\nST  - Short Title\nT2  - Academic Department\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Degree\nY2  - Access Date\nID  - 47\nER  - \n\n\nTY  - UNPB\nA2  - Editor, Series\nAB  - Abstract\nAD  - Author Address\nAU  - Name1, Author\nAU  - Name2, Author\nCA  - Caption\nCY  - Place Published\nDA  - Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nJ2  - Abbreviation\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Number\nM3  - Type of Work\nN1  - Notes\nPB  - Institution\nPY  - Year\nRN  - Research Notes\nSP  - Pages\nST  - Short Title\nT2  - Series Title\nT3  - Department\nTA  - Author, Translated\nTI  - Title of Work\nTT  - Translated Title\nUR  - URL\nY2  - Access Date\nID  - 48\nER  - \n\n\nTY  - WEB\nA2  - Editor, Series\nAB  - Abstract\nAD  - Author Address\nAN  - Accession Number\nAU  - Name1, Author\nAU  - Name2, Author\nC1  - Year Cited\nC2  - Date Cited\nCA  - Caption\nCN  - Call Number\nCY  - Place Published\nDA  - Last Update Date\nDB  - Name of Database\nDO  - DOI\nDP  - Database Provider\nET  - Edition\nJ2  - Periodical Title\nKW  - Keyword1, Keyword2, Keyword3\nKeyword4; Keyword5\nLA  - Language\nLB  - Label\nM1  - Access Date\nM3  - Type of Medium\nN1  - Notes\nOP  - Contents\nPB  - Publisher\nPY  - Year\nRN  - Research Notes\nSN  - ISBN\nSP  - Description\nST  - Short Title\nT2  - Series Title\nTA  - Author, Translated\nTI  - Title\nTT  - Translated Title\nUR  - URL\nVL  - Access Year\nID  - 49\nER  - \n"""

test_input_4 = """TY - JOUR\nAB - Optimal integration of next-generation sequencing into mainstream research requires re-evaluation of how problems can be reasonably overcome and what questions can be asked. .... The random sequencing-based approach to identify microsatellites was rapid, cost-effective and identified thousands of useful microsatellite loci in a previously unstudied species.\nAD - Consortium for Comparative Genomics, Department of Biochemistry and Molecular Genetics, University of Colorado School of Medicine, Aurora, CO 80045, USA; Department of Biology, University of Central Florida, 4000 Central Florida Blvd., Orlando, FL 32816, USA; Department of Biology & Amphibian and Reptile Diversity Research Center, The University of Texas at Arlington, Arlington, TX 76019, USA\nAU - CASTOE, TODD A.\nAU - POOLE, ALEXANDER W.\nAU - GU, WANJUN\nAU - KONING, A. P. JASON de\nAU - DAZA, JUAN M.\nAU - SMITH, ERIC N.\nAU - POLLOCK, DAVID D.\nL1 - internal-pdf://2009 Castoe Mol Eco Resources-1114744832/2009 Castoe Mol Eco Resources.pdf\ninternal-pdf://sm001-1634838528/sm001.pdf\ninternal-pdf://sm002-2305927424/sm002.txt\ninternal-pdf://sm003-2624695040/sm003.xls\nM1 - 9999\nN1 - 10.1111/j.1755-0998.2009.02750.x\nPY - 2009\nSN - 1755-0998\nST - Rapid identification of thousands of copperhead snake (Agkistrodon contortrix) microsatellite loci from modest amounts of 454 shotgun genome sequence\nT2 - Molecular Ecology Resources\nTI - Rapid identification of thousands of copperhead snake (Agkistrodon contortrix) microsatellite loci from modest amounts of 454 shotgun genome sequence\nUR - http://dx.doi.org/10.1111/j.1755-0998.2009.02750.x\nVL - 9999\nID - 3\nER -
"""

test_input_5 = """TY  - BILL\nN1  - Record ID: 10\nA1  - Author Name, Author2 Name2\nTI  - Act Name\nRP  - Reprint Status, Date\nCY  - Code\nPY  - Date of Code\nY2  - Date\nVL  - Bill/Res Number\nSP  - Section(s)\nN1  - Histroy: History\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - ART\nN1  - Record ID: 20\nA1  - Author Name, Author2 Name2\nN1  - Artist Role: Artist Role\nT1  - Title/Subject\nM1  - Medium\nN1  - Connective Phrase: Connective Phrase\nN1  - Author, Monographic: Monographic Author\nN1  - Author Role: Author Role\nN1  - Title Monographic: Monographic Title\nRP  - Reprint Status, Date\nVL  - Edition\nCY  - Place of Publication\nPB  - Publisher Name\nY1  - Date of Publication\nN1  - Location in Work: Location in Work\nN1  - Size: Size\nN1  - Series Title: Series Title\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\n\nTY  - ADVS\nN1  - Record ID: 30\nA1  - Author Name, Author2 Name2\nN1  - Author Role: Author Role\nT1  - Analytic Title\nM3  - Medium Designator\nN1  - Connective Phrase: Connective Phrase\nN1  - Author, Monographic: Monographic Author\nN1  - Author Role: Monographic Author Role\nN1  - Title Monographic: Monographic Title\nRP  - Reprint Status, Date\nVL  - Edition\nN1  - Author, Subsidiary: Subsidiary Author\nN1  - Author Role: Author Role\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nIS  - Volume ID\nN1  - Location in Work: Location in Work\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Size: Size\nN1  - Series Editor: Series Editor\nN1  - Series Editor Role: Series Editor Role\nN1  - Series Title: Series Title\nN1  - Series Volume ID: Series Volume ID\nN1  - Series Issue ID: Series Issue ID\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - CHAP\nN1  - Record ID: 40\nA1  - Author Name, Author2 Name2\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nA2  - Monographic Author\nN1  - Author Role: Author Role\nT2  - Monographic Title\nRP  - Reprint Status, Date\nVL  - Edition\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nN1  - Volume ID: Volume ID\nN1  - Issue ID: Issue ID\nSP  - Page(s)\nA3  - Series Editor\nN1  - Series Editor Role: Series Editor Role\nN1  - Series Title: Series Title\nN1  - Series Volume ID: Series Volume Identification\nN1  - Series Issue ID: Series Issue Identification\nN1  - Connective PhraseConnective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - CHAP\nN1  - Record ID: 50\nA1  - Author Name, Author2 Name2\nN1  - Author Role: Author Role\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nA2  - Monographic Author\nN1  - Author Role: Author Role\nT2  - Monographic Title\nRP  - Reprint Status, Date\nVL  - Edition\nN1  - Author, Subsidiary: Subsidiary Author\nN1  - Author Role: Author Role\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nN1  - Date of Copyright: Date of Copyright\nN1  - Volume ID: Volume ID\nN1  - Issue ID: Issue ID\nSP  - Page(s)\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nA3  - Series Editor\nN1  - Series Editor Role: Series Editor Role\nT3  - Series Title\nN1  - Series Volume ID: Series Volume ID\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - ABST\nN1  - Record ID: 180\nA1  - Author Name, Author2 Name2\nT1  - Title\nJF  - Journal Title\nRP  - Reprint Status, Date\nY1  - Date of Publication\nVL  - Volume ID\nIS  - Issue ID\nSP  - Page(s)\nAD  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - BOOK\nN1  - Record ID: 190\nA1  - Monographic Author\nT1  - Monographic Title\nRP  - Reprint Status, Date\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - BOOK\nN1  - Record ID: 200\nA1  - Monographic Author\nN1  - Author Role: Author Role\nT1  - Monographic Title\nN1  - Translated Title: Translated Title\nRP  - Reprint Status, Date\nVL  - Edition\nN1  - Author, Subsidiary: Subsidiary Author\nN1  - Author Role: Author Role\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nN1  - Original Pub Date: Original Pub Date\nIS  - Volume ID\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nA3  - Series Editor\nN1  - Series Editor Role: Series Editor Role\nT3  - Series Title\nN1  - Series Volume ID: Series Volume ID\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - CASE\nN1  - Record Number: 210\nA1  - Counsel\nT1  - Case Name\nT2  - Case Name (Abbrev)\nRP  - Reprint Status, Date\nCY  - Reporter\nPB  - Court\nPY  - Date Field\nY2  - Date Decided\nN1  - First Page: First Page\nVL  - Reporter Number\nSP  - Page(s)\nT3  - History\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - COMP\nN1  - Record Number: 220\nT1  - Program Title\nN1  - Computer Program: Computer Program\nN1  - Connective Phrase: Connective Phrase\nA1  - Author/Programmer\nN1  - Author Role: Author Role\nN1  - Title: Title\nRP  - Reprint Status, Date\nIS  - Version\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nN1  - Date of Copyright: Date of Copyright\nN1  - Report Identification: Report ID\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - CONF\nN1  - Record Number: 230\nA1  - Author Name, Author2 Name2\nN1  - Author Role: Author Role\nN1  - Author Affiliation, Ana.: Author Affiliation\nT1  - Paper/Section Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nA2  - Editor/Compiler\nN1  - Editor/Compiler Role: Editor/Compiler Role\nN1  - Proceedings Title: Proceedings Title\nY2  - Date of Meeting\nN1  - Place of Meeting: Place of Meeting\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nN1  - Date of Copyright: Date of Copyright\nVL  - Volume ID\nSP  - Location in Work\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nA3  - Series Editor\nN1  - Series Editor Role: Series Editor Role\nT3  - Series Title\nN1  - Series Volume ID: Series Volume ID\nAV  - Address/Availability\nUR  - Location/URL\nN1  - ISBN: ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - DATA\nN1  - Record Number: 240\nT1  - Analytic Title\nN1  - Medium (Data File): Medium (Data File)\nN1  - Connective Phrase: Connective Phrase\nA2  - Editor/Compiler\nN1  - Editor/Compiler Role: Editor/Compiler Role\nN1  - Title, Monographic: Monographic Title\nRP  - Reprint Status, Date\nIS  - Version\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nSP  - Location in Work\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nT3  - Series Title\nN1  - Series Volume ID: Series Volume ID\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - THES\nN1  - Record Number: 250\nA1  - Author Name, Author2 Name2\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nRP  - Reprint Status, Date\nN1  - Place of Publication: Place of Publication\nPB  - University\nPY  - Date of Publication\nN1  - Date of Copyright: Date of Copyright\nSP  - Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - ELEC\nN1  - Record Number: 260\nA1  - Author Name, Author2 Name2\nT1  - Title\nM1  - Medium\nJO  - Source\nRP  - Reprint Status, Date\nIS  - Edition\nPB  - Publisher Name\nPY  - Last Update\nY2  - Access Date\nN1  - Volume ID: Volume ID\nSP  - Page(s)\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - ICOMM\nN1  - Record Number: 270\nA1  - Author Name, Author2 Name2\nN1  - Author E-mail: Author E-mail\nN1  - Author Affiliation: Author Affiliation\nT1  - Subject\nA2  - Recipient\nN1  - Recipient E-mail: Recipient E-mail\nRP  - Reprint Status, Date\nPY  - Date of Message\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - GEN\nN1  - Record Number: 280\nA1  - Author Name, Author2 Name2\nT1  - Analytic Title\nA2  - Monographic Author\nT2  - Monographic Title\nJO  - Journal Title\nRP  - Reprint Status, Date\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nY2  - Date of Copyright\nVL  - Volume ID\nIS  - Issue ID\nSP  - Location in Work\nA3  - Series Editor\nT3  - Series Title\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISSN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - HEAR\nN1  - Record Number: 290\nA1  - Author Name, Author2 Name2\nN1  - Author Role: Author Role\nN1  - Author Affiliation: Author Affiliation\nT1  - Title\nN1  - Medium Designator: Medium Designator\nRP  - Reprint Status, Date\nCY  - Committee\nPB  - Subcommittee\nPY  - Hearing Date\nY2  - Date\nVL  - Bill Number\nN1  - Issue ID: Issue ID\nN1  - Location in Work: Location/URL\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - MGZN\nN1  - Record Number: 300\nA1  - Author Name, Author2 Name2\nT1  - Article Title\nJO  - Magazine Title\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nN1  - Copyright Date: Date of Copyright\nVL  - Volume ID\nIS  - Issue ID\nSP  - Page(s)\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - INPR\nN1  - Record Number: 310\nA1  - Author Name, Author2 Name2\nT1  - Title\nJO  - Journal Title\nRP  - Reprint Status, Date\nPY  - Date of Publication\nN1  - Volume ID: Volume ID\nN1  - Page(s): Page(s)\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - JOUR\nN1  - Record Number: 320\nA1  - Author Name, Author2 Name2\nT1  - Article Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nJF  - Journal Title\nN1  - Translated Title: Translated Title\nRP  - Reprint Status, Date\nPY  - Date of Publication\nVL  - Volume ID\nIS  - Issue ID\nSP  - Page(s)\nN1  - Language: Language\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISSN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - JOUR\nN1  - Record Number: 330\nA1  - Author Name, Author2 Name2\nN1  - Author Role: Author Role\nN1  - Author Affiliation: Author Affiliation\nT1  - Article Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nN1  - Author, Monographic: Monographic Author\nN1  - Author Role: Author Role\nJF  - Journal Title\nRP  - Reprint Status, Date\nPY  - Date of Publication\nVL  - Volume ID\nIS  - Issue ID\nSP  - Page(s)\nAV  - Address/Availability\nUR  - Location/URL\nN1  - CODEN: CODEN\nSN  - ISSN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - JOUR\nN1  - Record Number: 340\nA1  - Author Name, Author2 Name2\nT1  - Analytic Title\nJF  - Journal Title\nRP  - Reprint Status, Date\nPY  - Date of Publication\nVL  - Volume ID\nIS  - Issue ID\nSP  - Page(s)\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISSN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - JFULL\nN1  - Record Number: 350\nN1  - Editor: Editor\nJF  - Journal Title\nRP  - Reprint Status, Date\nN1  - Medium Designator: Medium Designator\nN1  - Edition: Edition\nN1  - Place of Publication: Place of Publication\nN1  - Publisher Name: Publisher Name\nPY  - Date of Publication\nVL  - Volume ID\nIS  - Issue ID\nSP  - Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Frequency of Publication: Frequency of Publication\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - CODEN: CODEN\nSN  - ISSN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - PCOMM\nN1  - Record Number: 360\nA1  - Author Name, Author2 Name2\nN1  - Author Affiliation: Author Affiliation\nN1  - Medium Designator: Medium Designator\nA2  - Recipient\nRP  - Reprint Status, Date\nN1  - Place of Publication: Place of Publication\nPY  - Date of Letter\nN1  - Extent of Letter: Extent of Letter\nN1  - Packaging Method: Packaging Method\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - SER\nN1  - Record Number: 370\nA1  - Author Name, Author2 Name2\nN1  - Author Role: Author Role\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nT3  - Collection Title\nRP  - Reprint Status, Date\nPY  - Date of Publication\nSP  - Location of Work\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Document Type: Document Type\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - MAP\nN1  - Record Number: 380\nT1  - Map Title\nM2  - Map Type\nA1  - Cartographer\nN1  - Cartographer Role: Cartographer Role\nRP  - Reprint Status, Date\nM1  - Area\nN1  - Medium Designator: Medium Designator\nVL  - Edition\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nY2  - Date of Copyright\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Size: Size\nN1  - Scale: Scale\nT3  - Series Title\nN1  - Series Volume ID: Series Volume ID\nN1  - Series Issue ID: Series Issue ID\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - SER\nN1  - Record Number: 390\nA1  - Monographic Author\nN1  - Author Role: Author Role\nT1  - Monographic Title\nRP  - Reprint Status, Date\nVL  - Edition\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - MUSIC\nN1  - Record Number: 400\nA1  - Composer\nN1  - Composer Role: Composer Role\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nA2  - Editor/Compiler\nN1  - Editor/Compiler Role: Editor/Compiler Role\nN1  - Title, Monographic: Monographic Title\nRP  - Reprint Status, Date\nN1  - Medium Designator: Medium Designator\nVL  - Edition\nN1  - Author, Subsidiary: Subsidiary Author\nN1  - Author Role: Author Role\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nN1  - Copyright Date: Copyright Date\nIS  - Volume ID\nN1  - Report Identification: Report ID\nN1  - Plate Number: Plate Number\nN1  - Location in Work: Location in Work\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nA3  - Series Editor\nN1  - Series Editor Role: Series Editor Role\nT3  - Series Title\nN1  - Series Volume ID: Series Volume ID\nN1  - Series Issue ID: Series Issue ID\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - MPCT\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nN1  - Producer: Producer\nN1  - Producer Role: Producer Role\nRP  - Reprint Status, Date\nA1  - Director\nN1  - Director Role: Director Role\nCY  - Place of Publication\nU5  - Distributor\nPY  - Date of Publication\nM2  - Timing\nN1  - Packaging Method: Packaging Method\nN1  - Size: Size\nT3  - Series Title\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - NEWS\nN1  - Record Number: 420\nA1  - Author Name, Author2 Name2\nN1  - Author Role: Author Role\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nJO  - Newspaper Name\nRP  - Reprint Status, Date\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nM2  - Section\nN1  - Column Number: Column Number\nSP  - Page(s)\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\n\nTY  - PAT\nN1  - Record Number: 430\nA1  - Inventor Name\nN1  - Address: Address\nT1  - Patent Title\nA2  - Assignee\nN1  - Title, Short Form: Title, Short Form\nN1  - Title, Long Form: Title, Long Form\nN1  - Abstract Journal Date: Abstract Journal Date\nCY  - Country\nM3  - Document Type\nIS  - Patent Number\nN1  - Abstract Journal Title: Abstract Journal Title\nPY  - Date of Patent Issue\nVL  - Application No./Date\nN1  - Abstract Journal Volume: Abstract Journal Volume\nN1  - Abstract Journal Issue: Abstract Journal Issue\nSP  - Abstract Journal Page(s)\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Language: Language\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nM2  - Class Code, National\nM1  - Class Code, International\nN1  - Related Document No.: Related Document Number\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Registry Number: Registry Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\n\nTY  - RPRT\nN1  - Record Number: 440\nA1  - Author Name, Author2 Name2\nN1  - Author Role, Analytic: Author Role\nN1  - Author Affiliation: Author Affiliation\nN1  - Section Title: Section Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nA2  - Monographic Author\nN1  - Author Role: Author Role\nT1  - Report Title\nRP  - Reprint Status, Date\nN1  - Edition: Edition\nN1  - Author, Subsidiary: Subsidiary Author\nN1  - Author Role: Author Role\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nVL  - Report ID\nSP  - Extent of Work\nN1  - Packaging Method: Packaging Method\nT3  - Series Title\nN1  - Series Volume ID: Series Volume ID\nN1  - Series Issue ID: Series Issue ID\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - CODEN: CODEN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\n\nTY  - SOUND\nN1  - Record Number: 450\nA1  - Composer\nN1  - Composer Role: Composer Role\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nN1  - Connective Phrase: Connective Phrase\nN1  - Editor/Compiler: Editor/Compiler\nN1  - Editor/Compiler Role: Editor/Compiler Role\nN1  - Recording Title: Recording Title\nRP  - Reprint Status, Date\nN1  - Edition: Edition\nA2  - Performer\nN1  - Performer Role: Performer Role\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nN1  - Copyright Date: Date of Copyright\nN1  - Acquisition Number: Acquisition Number\nN1  - Matrix Number: Matrix Number\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Size: Size\nN1  - Reproduction Ratio: Reproduction Ratio\nT3  - Series Title\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\n\nTY  - STAT\nN1  - Record Number: 460\nA1  - Author Name, Author2 Name2\nT1  - Statute Title\nRP  - Reprint Status, Date\nCY  - Code\nPY  - Date of Publication\nY2  - Date\nVL  - Title/Code Number\nSP  - Section(s)\nT3  - History\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - CTLG\nN1  - Record Number: 470\nA1  - Author Name, Author2 Name2\nT1  - Catalog Title\nN1  - Medium Designator: Medium Designator\nRP  - Reprint Status, Date\nVL  - Edition\nCY  - Place of Publication\nPB  - Publisher Name\nPY  - Date of Publication\nIS  - Catalog Number\nN1  - Issue Identification: Issue ID\nN1  - Extent of Work: Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\n\nTY  - UNBILL\nN1  - Record Number: 480\nA1  - Author Name, Author2 Name2\nT1  - Act Title\nRP  - Reprint Status, Date\nCY  - Code\nPY  - Date of Code\nY2  - Date\nVL  - Bill/Res Number\nT3  - History\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - UNPB\nN1  - Record Number: 490\nA1  - Author Name, Author2 Name2\nT1  - Title\nA2  - Editor(s)\nRP  - Reprint Status, Date\nPY  - Date of Publication\nN1  - Date of Copyright: Date of Copyright\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\nTY  - VIDEO\nN1  - Record Number: 500\nA1  - Author Name, Author2 Name2\nT1  - Analytic Title\nN1  - Medium Designator: Medium Designator\nN1  - Producer: Producer\nN1  - Producer Role: Producer Role\nRP  - Reprint Status, Date\nN1  - Director: Director\nN1  - Director Role: Director Role\nCY  - Place of Publication\nPB  - Distributor\nPY  - Date of Publication\nM2  - Extent of Work\nN1  - Packaging Method: Packaging Method\nN1  - Size: Size\nT3  - Series Title\nN1  - Connective Phrase: Connective Phrase\nAV  - Address/Availability\nUR  - Location/URL\nSN  - ISBN\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\n\nTY  - ELEC\nN1  - Record Number: 510\nA1  - Author Name, Author2 Name2\nN1  - Author Role: Author Role\nN1  - Author Affiliation: Author Affiliation\nT1  - Title\nRP  - Reprint Status, Date\nPY  - Date of Publication\nY2  - Date of Access\nAV  - Address/Availability\nUR  - Location/URL\nN1  - Notes: Notes\nN2  - Abstract\nN1  - Call Number: Call Number\nKW  - Keywords1, Keywords2, Keywords3\nKW  - Keywords4\nER  - \n\n
"""

test_input_6 = """TY  - JOUR\nT1  - From Basic to Applied Research to Improve Outcomes for Individuals Who Require Augmentative and Alternative Communication: \u2028Potential Contributions of Eye Tracking Research Methods\nAU  - Light, Janice\nAU  - McNaughton, David\nY1  - 2014/06/01\nPY  - 2014\nDA  - 2014/06/01\nN1  - doi: 10.3109/07434618.2014.906498\nDO  - 10.3109/07434618.2014.906498\nT2  - Augmentative and Alternative Communication\nJF  - Augmentative and Alternative Communication\nJO  - Augment Altern Commun\nSP  - 99\nEP  - 105\nVL  - 30\nIS  - 2\nPB  - Informa Allied Health\nSN  - 0743-4618\nM3  - doi: 10.3109/07434618.2014.906498\nUR  - http://dx.doi.org/10.3109/07434618.2014.906498\nY2  - 2014/12/17\nER  - """

test_input_7 = """TY  - BOOK\nSN  - 9783642002304\nAU  - Depenheuer, Otto\nT1  - Eigentumsverfassung und Finanzkrise\nT2  - Bibliothek des Eigentums\nPY  - 2009\nCY  - Berlin, Heidelberg\nPB  - Springer Berlin Heidelberg\nKW  - Finanzkrise / Eigentum / Haftung / Ordnungspolitik / Aufsatzsammlung / Online-Publikation\nKW  - Constitutional law\nKW  - Law\nUR  - http://dx.doi.org/10.1007/978-3-642-00230-4\nL1  - doi:10.1007/978-3-642-00230-4\nVL  - 7\nAB  - In dem Buch befinden sich einzelne Beiträge zu ...\nLA  - ger\nH1  - UB Mannheim\nH2  - 300 QN 100 D419\nH1  - UB Leipzig\nH2  - PL 415 D419\nTS  - BibTeX\nDO  - 10.1007/978-3-642-00230-4\nER  -\n\n"""



def ris_text_read(textChunk):
    """
    params: textChunk, str.
    return: ris_text_list, []

    Recipe adapted from the code published by pyInTheSky on 2011-09-26 taken from SO:
    http://stackoverflow.com/questions/7559397/python-read-file-from-and-to-specific-lines-of-text
    """
    #
    line_begin = "TY"
    line_end = "ER"
    #
    ris_text_list = re.findall('(TY  -.*?\nER )', textChunk, re.S)
    #
    return ris_text_list


def ris_text_parse(ris_text):
    """
    params: ris_text,str.
    return: ris_text_line_list, {}
    """
    #
    ris_text_lines = ris_text.splitlines()
    #
    # SP  - 79, EP  - 96, SN  - 0392-4866
    # ["SP  "," 79",], ["EP  "," 96"], ["SN  ","0392","4866"] !!
    #
    changed_ris_text_lines = []
    for ris_text_line in ris_text_lines:
        try:
            re.match("^([A-Z1-9]+)", ris_text_line)
            #
            if re.match("^([A-Z1-9]+)", ris_text_line) is None:
                raise ValueError("The line doesn't start with a ris element. Make sure ris file has been divided: 'Ris_Tag CorrespondingValue lineDelimiter' structure")
        except ValueError as ris_text_line_split_fail:
            #
            print(ris_text_line_split_fail)
            print("Trying a hack that might or might not work. In any case you should, see the original line. I will give its index but it will not be available after our method, apply the index number to the original file after you have try to split it with .split('\\n') method.")
            print("Index no:\n")
            print(str(ris_text_lines.index(ris_text_line)))
            index_ris_text_line = ris_text_lines.index(ris_text_line)
            ris_text_lines[index_ris_text_line-1] = ris_text_lines[index_ris_text_line-1] + ris_text_line
            ris_text_lines.remove(ris_text_line)
        else:
            changed_ris_text_lines.append(ris_text_line)
            pass
    #
    ris_lines_split = [ris_line.split("-") for ris_line in changed_ris_text_lines]
    ris_text_line_list = []
    #
    for ris_line_list in ris_lines_split:
        if len(ris_line_list) == 2:
            # ["EP  "," 96"]
            #
            ris_line = [ris_element.strip() for ris_element in ris_line_list]
            if ris_line[0] == "ER":
                ris_lines_split.remove(ris_line_list)
                continue
            ris_text_line_list.append(ris_line)
            #
        elif len(ris_line_list) > 2:
            # ["SN  ","0392","4866"]
            #
            ris_line = [ris_line_list[0].strip(), ris_line_list[1]+ "-".join(ris_line_list[1:])]
            ris_text_line_list.append(ris_line)
            #
    #
    return ris_text_line_list


def risType_map(ris_text_line_list, ris_types_map_dict):
    """
    params:
    ris_text_line_list, [[],[],[], ...]
    ris_types_map_dict , {}

    return: ris_text_line_list_dict, [{},[],[],[], ...]
    """
    #
    ris_text_line_dict_list = []
    for ris_line in ris_text_line_list:
        if ris_line[1] in ris_types_map_dict.keys():
            ris_type = {}
            ris_type["itemType"] = ris_types_map_dict[ris_line[1]]
            ris_text_line_dict_list.append(ris_type)
        else:
            ris_text_line_dict_list.append(ris_line)
    #
    return ris_text_line_dict_list


def risIndependentField_map(ris_text_line_list, ris_fields_dict):
    """
    params:
    ris_text_line_list, [[],[],[], ...]
    ris_fields_dict , {}

    return: ris_text_line_list_dict, [{},[],[],[], ...]
    """
    #
    ris_text_line_dict_list = []
    for ris_line in ris_text_line_list:
        if isinstance(ris_line, dict):
            ris_text_line_dict_list.append(ris_line)
            continue
        elif ris_line[0] in ris_fields_dict.keys():
            ris_type = {}
            ris_key_value = ris_fields_dict[ris_line[0]].strip()
            ris_type[ris_key_value] = ris_line[1].strip()
            ris_text_line_dict_list.append(ris_type)
        else:
            ris_text_line_dict_list.append(ris_line)
    #
    return ris_text_line_dict_list


def ris_itemType_get(ris_text_line_dict_list):
    """
    params: ris_text_line_list_dict, [{},[],[],[], ...]
    return: itemType_value, str.
    """
    #
    itemType_list = []
    for ris_element in ris_text_line_dict_list:
        if isinstance(ris_element, dict):
            if "itemType" in ris_element.keys():
                itemType_list.append(ris_element["itemType"])
            else:
                pass
        else:
            pass
    #
    itemType_value = itemType_list[0]
    #
    return itemType_value

def ris_DependentField_get(risTag, dependent_field_map):
    """
    params:
    dependent_field_map, [{a:
    {b:[], c:d, f:[]
    }
    }, {}, ...]
    risTag, str.

    return: ris_text_line_dict, {}
    """
    #
    dependent_field_dict = {}
    if risTag in dependent_field_map.keys():
        dependent_field_dict[risTag] = dependent_field_map[risTag]
        #
    #
    return dependent_field_dict


def ris_DependentField_parse(dependent_field_dict, dependent_field_map):
    """
    params:
    dependent_field_dict, {}.
    itemType_value, str.

    return:
    fieldsTuple = (default_value_list,[]
    exclude_value_list, []
    ignore_value_list, []
    other_risTag_value_list, [])
    """
    #
    default_value_list = []
    exclude_value_list = []
    ignore_value_list = []
    other_risTag_value_list = []
    dd_tuple = tuple(dependent_field_dict.items())[0]
    #
    if isinstance(dd_tuple[1], dict):
            if "__default" in dd_tuple[1].keys():
                default_value_list.append(dd_tuple[1]["__default"])
                # appends string value
            elif "__exclude" in dd_tuple[1].keys():
                exclude_value_list.append(dd_tuple[1]["__exclude"])
                # appends list value
            elif "__ignore" in dd_tuple[1].keys():
                ignore_value_list.append(dd_tuple[1]["__ignore"])
                # appends a list but some tag, ID has ignore as value
            for value, itemType_list in dd_tuple[1].items():
                if value != "__default" and value != "__exclude" and value != "__ignore":
                    risTag_value_dict = {}
                    risTag_value_dict[value] = itemType_list
                    other_risTag_value_list.append(risTag_value_dict)
                else:
                    pass
            fieldsTuple = (dd_tuple[0], default_value_list, exclude_value_list, ignore_value_list, other_risTag_value_list)
            #
    elif dd_tuple[1] == "__ignore":
        fieldsTuple = ("ID", default_value_list, exclude_value_list, ignore_value_list, other_risTag_value_list)
    #
    elif dd_tuple[1] == "AU" or dd_tuple[1] == "TI" or dd_tuple[1] == "DA" or dd_tuple[1] == "ET":
        # AU in "A1":"AU"
        new_dependent_field_dict = ris_DependentField_get(dd_tuple[1], dependent_field_map=dependent_field_map)
        new_dd_tuple = tuple(new_dependent_field_dict.items())[0]
        if "__default" in new_dd_tuple[1].keys():
            default_value_list.append(new_dd_tuple[1]["__default"])
            # appends string value
        elif "__exclude" in new_dd_tuple[1].keys():
            exclude_value_list.append(new_dd_tuple[1]["__exclude"])
            # appends list value
        elif "__ignore" in new_dd_tuple[1].keys():
            ignore_value_list.append(new_dd_tuple[1]["__ignore"])
            # appends a list but some tag, ID has ignore as value
        for value, itemType_list in new_dd_tuple[1].items():
            if value != "__default" and value != "__exclude" and value != "__ignore":
                risTag_value_dict = {}
                risTag_value_dict[value] = itemType_list
                other_risTag_value_list.append(risTag_value_dict)
            else:
                pass
        fieldsTuple = (new_dd_tuple[0], default_value_list, exclude_value_list, ignore_value_list, other_risTag_value_list)
    else:
        fieldsTuple = None
            #
    #
    return fieldsTuple


def ris_excludeValue_check(fieldsTuple, itemType_value):
    """
    params:
    fieldsTuple, tuple.
    itemType_value, str.

    return: fieldValue_dict, {}
    """
    #
    ris_element = fieldsTuple[0]
    exclude_value_list = fieldsTuple[2]
    fieldValue_dict = {}
    #
    for exclude_value in exclude_value_list:
        if itemType_value in exclude_value:
            if ris_element == "CY" and itemType_value == "conferencePaper":
                fieldValue_dict["C1"] = False
            elif ris_element == "NV" and itemType_value == "bookSection":
                fieldValue_dict["IS"] = False
            elif ris_element == "SE" and itemType_value == "case":
                fieldValue_dict["SE"] = True
                pass
            elif ris_element == "VL" and itemType_value == "patent":
                fieldValue_dict["VL"] = True
                pass
            elif ris_element == "VL" and itemType_value == "webpage":
                fieldValue_dict["VL"] = True
                pass
            else:
                pass
        elif itemType_value not in exclude_value_list:
            fieldValue_dict[ris_element] = False
        else:
            pass
        #
    #
    return fieldValue_dict


def ris_StandardDependentField_itemType_get(fieldsTuple, itemType_value):
    """
    params: fieldsTuple, ()
    itemType_value, str.

    return: fieldVaule_dict, {}
    """
    #
    ris_element = fieldsTuple[0]
    other_risTag_value_list = fieldsTuple[4]
    fieldValue_dict = {}
    for risTag_value in other_risTag_value_list:
        for value, itemTypes in risTag_value.items():
            if isinstance(itemTypes, list):
                if itemType_value in itemTypes:
                    fieldValue_dict[ris_element] = value
                else:
                    pass
            else:
                pass
            #
    #
    return fieldValue_dict

def ris_defaultValue_get(fieldsTuple):
    """
    params: fieldsTuple, ()
    return: fieldVaule_dict, {}
    """
    #
    ris_element = fieldsTuple[0]
    if len(fieldsTuple[1]) != 0:
        default_value = fieldsTuple[1][0]
    else:
        default_value = []
    fieldValue_dict = {}
    fieldValue_dict[ris_element] = default_value
    #
    return fieldValue_dict


def ris_ignoreValue_check(fieldsTuple, itemType_value):
    """
    params:
    fieldsTuple, ()
    itemType_value, str.

    return: fieldValue_dict
    """
    #
    ris_element = fieldsTuple[0]
    ignore_value_list = fieldsTuple[2]
    fieldValue_dict = {}
    #
    for ignore_value in ignore_value_list:
        if itemType_value in ignore_value:
            fieldValue_dict[ris_element] = True
        else:
            fieldValue_dict[ris_element] = False
        #
    #
    return fieldValue_dict



def ris_DependentField_itemType_get(fieldsTuple, itemType_value, dependent_field_map):
    """
    params: fieldsTuple, ()
    itemType_value, str.

    return: fieldVaule_dict, {}
    """
    #
    default_value_get = ris_defaultValue_get(fieldsTuple)
    ignore_value_check = ris_ignoreValue_check(fieldsTuple, itemType_value)
    exclude_value_check = ris_excludeValue_check(fieldsTuple, itemType_value)
    standard_dep_field_get = ris_StandardDependentField_itemType_get(fieldsTuple, itemType_value)
    fieldValue_dict = {}
    #
    # Rearrange depending on the Checks -----------------
    #
    # Best Case Scenario: No exclude nor Ignore -----------------------
    if len(ignore_value_check) == 0 and len(exclude_value_check) == 0 and len(standard_dep_field_get) == 0:
        fieldValue_dict = default_value_get
    elif len(ignore_value_check) == 0 and len(exclude_value_check) == 0 and len(standard_dep_field_get) > 0:
        fieldValue_dict = standard_dep_field_get
        # Exclude case ---------------------------------
    elif len(ignore_value_check) == 0 and len(exclude_value_check) > 0:
        for exclude_key, value in exclude_value_check.items():
            if value is True:
                exclude_new_Ristag_Fields = ris_DependentField_get(exclude_key, dependent_field_map)
                exclude_new_Ristag_field_parse = ris_DependentField_parse(exclude_new_Ristag_Fields, dependent_field_map)
                exclude_new_value = ris_StandardDependentField_itemType_get(exclude_new_Ristag_field_parse, itemType_value)
                exclude_new_default_value = ris_defaultValue_get(exclude_new_Ristag_field_parse)
                if len(exclude_new_value) == 0:
                    fieldValue_dict = exclude_new_default_value
                elif len(exclude_new_value) > 0:
                    fieldValue_dict = exclude_new_value
                    #
        # Ignore Case -----------------------------------
    elif len(ignore_value_check) > 0:
        for ris_element, ignore_value in ignore_value_check.items():
            if ignore_value is True:
                fieldValue_dict[ris_element] = None
    #
    return fieldValue_dict


def risDependentField_map(ris_text_line_dict_list, dependent_field_map):
    """
    params:
    ris_text_line_dict_list, [{},[],[],[], ...]
    return:
    """
    #
    itemType_value = ris_itemType_get(ris_text_line_dict_list)
    #
    ris_text_line_parse = []
    for ris_text_line in ris_text_line_dict_list:
        if isinstance(ris_text_line, list):
            if ris_text_line[0] == "ID":
                ris_text_line_dict_list.remove(ris_text_line)
                continue
            relevant_tag_info = ris_DependentField_get(ris_text_line[0], dependent_field_map)
            relevant_tag_parse = ris_DependentField_parse(relevant_tag_info, dependent_field_map=dependent_field_map)
            relevant_tag_get = ris_DependentField_itemType_get(relevant_tag_parse, dependent_field_map=dependent_field_map, itemType_value=itemType_value)
            for relevant_tag, value in relevant_tag_get.items():
                if value is None and ris_text_line[0] == relevant_tag:
                    ris_text_line_dict_list.remove(ris_text_line)
                    continue
                    #
                else:
                    pass
            #
            ris_text_new_line = [relevant_tag_get, ris_text_line[1:]]
        else:
            ris_text_new_line = ris_text_line
        #
        ris_text_line_parse.append(ris_text_new_line)
        #
    return ris_text_line_parse


def ris_fieldMap(ris_text_line_parse):
    """
    params: ris_text_line_parse, [[{},[]],[{}[]], ...]
    return: ris_line_list, [[],[], ...]
    """
    #
    ris_line_list = []
    for ris_text_line in ris_text_line_parse:
        if isinstance(ris_text_line, list):
            ris_dict = ris_text_line[0]
            ris_dict_items_list = list(ris_dict.items())[0]
            zotero_type = ris_dict_items_list[1]
            ris_type = ris_dict_items_list[0]
            ris_value = ris_text_line[1][0]
            if ris_type == "RP":
                ris_line_list.append([zotero_type, "Reprint Edition. " + ris_value])
            else:
                ris_line_list.append([zotero_type, ris_value])
        else:
            ris_line_list.append(ris_text_line)
    #
    return ris_line_list


def ris_p_dict_map(ris_text, ris_types, ris_Indep_fields, ris_Dep_fields):
    """
    params:
    ris_text, str
    ris_types, dict
    ris_Indep_fields, dict
    ris_Dep_fields, dict

    return:
    ris_text_p_dict, dict
    """
    #
    ris_parsing_text = ris_text_parse(ris_text)
    ris_get_types = risType_map(ris_parsing_text, ris_types)
    ris_get_Indep_fields = risIndependentField_map(ris_get_types, ris_Indep_fields)
    ris_get_Dep_fields = risDependentField_map(ris_get_Indep_fields, ris_Dep_fields)
    ris_text_p_dict = ris_fieldMap(ris_get_Dep_fields)
    #
    return ris_text_p_dict


def pascal_francis_journal_zotero_map(PF_notice_elements_list):
    """
    params:
    PF_notice_elements_list, [[],{},[],[],{},[],{},{}, ...]

    return: zotero_dict_note_list, [{},{}]
    """
    #
    zotero_dict = {'DOI': '',
                   'ISSN': '',
                   'abstractNote': '',
                   'accessDate': '',
                   'archive': '',
                   'archiveLocation': '',
                   'callNumber': '',
                   'collections': [],
                   'creators': [{'creatorType': 'author', 'firstName': '', 'lastName': ''}],
                   'date': '',
                   'extra': '',
                   'issue': '',
                   'itemType': 'journalArticle',
                   'journalAbbreviation': '',
                   'language': '',
                   'libraryCatalog': '',
                   'pages': '',
                   'publicationTitle': '',
                   'relations': {},
                   'rights': '',
                   'series': '',
                   'seriesText': '',
                   'seriesTitle': '',
                   'shortTitle': '',
                   'tags': [],
                   'title': '',
                   'url': '',
    'volume': ''}
    zotero_note_list = []
    for pf_notice_elements in PF_notice_elements_list:
        if isinstance(pf_notice_elements, list) and pf_notice_elements[0] == "creators/author":
            name_author_brut = pf_notice_elements[1].strip()
            name_author_split = name_author_brut.split(",")
            if len (name_author_split) > 1:
                zotero_dict["creators"][0]['firstName'] = name_author_split[1].strip()
                zotero_dict["creators"][0]['lastName'] = name_author_split[0].strip()
            elif len(name_author_split) == 1:
                # For names that are wrongly provided as
                # J. J.-C GOYON GOYON
                name_author_new_split_brut = name_author_brut.split(" ")
                name_author_new_split = list(set(name_author_new_split_brut))
                name_first_name = ""
                name_last_name = ""
                for name_split in name_author_new_split:
                    if len(name_split) <= 2:
                        if name_split not in name_first_name:
                            name_first_name = name_first_name + " " + name_split
                    elif len(name_split) > 2 and re.match("[A-Z]\.-[A-Z]", name_split) is not None:
                        # For names like J.-P. Kollerin
                        if name_split not in name_first_name:
                            name_first_name = name_split
                    elif len(name_split) > 2 and re.match("\w\.-\w\.", name_split) is None:
                        if name_split not in name_last_name:
                            name_last_name = name_last_name + " " + name_split
                zotero_dict["creators"][0]['firstName'] = name_first_name.strip()
                zotero_dict["creators"][0]['lastName'] = name_last_name.strip()
        elif isinstance(pf_notice_elements, list) and pf_notice_elements[0] == "pages":
            zotero_dict["pages"] = pf_notice_elements[1].strip()
        elif isinstance(pf_notice_elements, list):
            if pf_notice_elements[0] in zotero_dict.keys():
                zotero_dict[pf_notice_elements[0]] = pf_notice_elements[1].strip()
            else:
                pass
        elif isinstance(pf_notice_elements, dict) and "archive" in pf_notice_elements.keys():
            zotero_dict["archive"] = pf_notice_elements["archive"].strip()
        elif isinstance(pf_notice_elements, dict) and "libraryCatalog" in pf_notice_elements.keys():
            zotero_dict["libraryCatalog"] = pf_notice_elements["libraryCatalog"].strip()
        elif isinstance(pf_notice_elements, dict) and "journalAbbreviation" in pf_notice_elements.keys():
            zotero_dict["journalAbbreviation"] = pf_notice_elements["journalAbbreviation"].strip()
        elif isinstance(pf_notice_elements, dict) and "pages" in pf_notice_elements.keys():
            zotero_dict["pages"] = zotero_dict["pages"].strip() + "-" + pf_notice_elements["pages"].strip()
        elif isinstance(pf_notice_elements, dict) and "abstractNote" in pf_notice_elements.keys():
            zotero_dict["abstractNote"] = pf_notice_elements["abstractNote"].strip()
        elif isinstance(pf_notice_elements, dict) and "notes" in pf_notice_elements.keys():
            zotero_note_dict = {}
            zotero_note_dict["collections"] = ["Anatolia"]
            zotero_note_dict["itemType"] = 'note'
            zotero_note_dict["note"] = pf_notice_elements["notes"].strip()
            zotero_note_dict["relations"] = {}
            zotero_note_dict["tags"] = []
            zotero_note_list.append(zotero_note_dict)
            #
    return [zotero_dict, zotero_note_list]


def pascal_francis_conference_zotero_map(PF_notice_elements_list):
    """
    params:
    PF_notice_elements_list, [[],{},[],[],{},[],{},{}, ...]

    return: zotero_dict_note_list, [{},{}]
    """
    #
    zotero_dict = {'DOI': '',
                   'ISBN': '',
                   'abstractNote': '',
                   'accessDate': '',
                   'archive': '',
                   'archiveLocation': '',
                   'callNumber': '',
                   'collections': [],
                   'conferenceName': '',
                   'creators': [{'creatorType': 'author', 'firstName': '', 'lastName': ''}],
                   'date': '',
                   'extra': '',
                   'itemType': 'conferencePaper',
                   'language': '',
                   'libraryCatalog': '',
                   'pages': '',
                   'place': '',
                   'proceedingsTitle': '',
                   'publisher': '',
                   'relations': {},
                   'rights': '',
                   'series': '',
                   'shortTitle': '',
                   'tags': [],
                   'title': '',
                   'url': '',
    'volume': ''}
    zotero_note_list = []
    for pf_notice_elements in PF_notice_elements_list:
        if isinstance(pf_notice_elements, list) and pf_notice_elements[0] == "creators/author":
            name_author_brut = pf_notice_elements[1].strip()
            name_author_split = name_author_brut.split(",")
            if len (name_author_split) > 1:
                zotero_dict["creators"][0]['firstName'] = name_author_split[1].strip()
                zotero_dict["creators"][0]['lastName'] = name_author_split[0].strip()
            elif len(name_author_split) == 1:
                # For names that are wrongly provided as
                # J. J.-C GOYON GOYON
                name_author_new_split_brut = name_author_brut.split(" ")
                name_author_new_split = list(set(name_author_new_split_brut))
                name_first_name = ""
                name_last_name = ""
                for name_split in name_author_new_split:
                    if len(name_split) <= 2:
                        if name_split not in name_first_name:
                            name_first_name = name_first_name + " " + name_split
                    elif len(name_split) > 2 and re.match("[A-Z]\.-[A-Z]", name_split) is not None:
                        # For names like J.-P. Kollerin
                        if name_split not in name_first_name:
                            name_first_name = name_split
                    elif len(name_split) > 2 and re.match("\w\.-\w\.", name_split) is None:
                        if name_split not in name_last_name:
                            name_last_name = name_last_name + " " + name_split
                zotero_dict["creators"][0]['firstName'] = name_first_name.strip()
                zotero_dict["creators"][0]['lastName'] = name_last_name.strip()
        elif isinstance(pf_notice_elements, list) and pf_notice_elements[0] == "pages":
            zotero_dict["pages"] = pf_notice_elements[1].strip()
        elif isinstance(pf_notice_elements, list):
            if pf_notice_elements[0] in zotero_dict.keys():
                zotero_dict[pf_notice_elements[0]] = pf_notice_elements[1].strip()
            else:
                pass
        elif isinstance(pf_notice_elements, dict) and "archive" in pf_notice_elements.keys():
            zotero_dict["archive"] = pf_notice_elements["archive"].strip()
        elif isinstance(pf_notice_elements, dict) and "libraryCatalog" in pf_notice_elements.keys():
            zotero_dict["libraryCatalog"] = pf_notice_elements["libraryCatalog"].strip()
        elif isinstance(pf_notice_elements, dict) and "journalAbbreviation" in pf_notice_elements.keys():
            zotero_dict["journalAbbreviation"] = pf_notice_elements["journalAbbreviation"].strip()
        elif isinstance(pf_notice_elements, dict) and "pages" in pf_notice_elements.keys():
            zotero_dict["pages"] = zotero_dict["pages"].strip() + "-" + pf_notice_elements["pages"].strip()
        elif isinstance(pf_notice_elements, dict) and "abstractNote" in pf_notice_elements.keys():
            zotero_dict["abstractNote"] = pf_notice_elements["abstractNote"].strip()
        elif isinstance(pf_notice_elements, dict) and "notes" in pf_notice_elements.keys():
            zotero_note_dict = {}
            zotero_note_dict["collections"] = ["Anatolia"]
            zotero_note_dict["itemType"] = 'note'
            zotero_note_dict["note"] = pf_notice_elements["notes"].strip()
            zotero_note_dict["relations"] = {}
            zotero_note_dict["tags"] = []
            zotero_note_list.append(zotero_note_dict)
        elif isinstance(pf_notice_elements, dict) and "tags" in pf_notice_elements.keys():
            tag_dict = {"tag":pf_notice_elements["tags"]}
            zotero_dict["tags"].append(tag_dict)
            #
    return [zotero_dict, zotero_note_list]


def pascal_francis_confP_map(notice_list, itemType=""):
    """
    params: notice_list, []
    itemType, str.

    return: zotero_item_list
    """
    #
    zotero_item_list = []
    for ris_notice in notice_list:
        for ris_not in ris_notice:
            if isinstance(ris_not, dict):
                if ris_not.get("itemType") == itemType:
                    try:
                        ris_not_zot_confP = pascal_francis_conference_zotero_map(ris_notice)
                    except IndexError:
                        print(ris_notice)
                        print(notice_list.index(ris_notice))
                        continue
                    else:
                        pass
                    zotero_item_list.append(ris_not_zot_confP)
                else:
                    pass
    #
    return zotero_item_list

def pascal_francis_journ_map(notice_list, itemType=""):
    """
    params: notice_list, []
    itemType, str.

    return: zotero_item_list
    """
    #
    zotero_item_list = []
    for ris_notice in notice_list:
        for ris_not in ris_notice:
            if isinstance(ris_not, dict):
                if ris_not.get("itemType") == itemType:
                    try:
                        ris_not_zot_jour = pascal_francis_journal_zotero_map(ris_notice)
                    except IndexError:
                        print(ris_notice)
                        print(notice_list.index(ris_notice))
                        continue
                    else:
                        pass
                    zotero_item_list.append(ris_not_zot_jour)
                else:
                    pass
    #
    return zotero_item_list


def zotero_collection_map(zotero_item_list, collection=""):
    """
    params: zotero_item_list, [{},{}, ...]
    return: zotero_item_collection_list, [{},{}, ...]
    """
    #
    zotero_item_collection_list = []
    for zotero_item in zotero_item_list:
        new_zotero_item_list = []
        for zot_item in zotero_item:
            if isinstance(zot_item, dict) and "collections" in zot_item.keys():
                zot_item["collections"].append(collection)
                new_zotero_item_list.append(zot_item)
        zotero_item_collection_list.append(new_zotero_item_list)
    #
    return zotero_item_collection_list


def zotero_note_update(resp, note_dict):
    """
    params:
    resp, {}
    note_dict, {}

    return: note_dict, {}
    """
    #
    parent_key = resp["success"]["0"]
    note_dict["parentItem"] = parent_key
    #
    return note_dict

def zotero_write_token():
    """
    str.
    """
    #
    token = str(uuid.uuid4().hex)
    #
    return token
