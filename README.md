# zotero-ris-to-json
Zotero Scripts to Convert Ris/Bibtex to Json
--------------------------------------------

Some fragile scripts to convert Ris/Bibtex to Json for facilitating use of Zotero API.

It has taken the field mapping from the original zotero [ris translator](https://github.com/zotero/translators/blob/master/RIS.js), some functions are also taken from [pyzotero](https://github.com/urschrei/pyzotero/blob/master/pyzotero/zotero.py) and from [bibtexparser](https://github.com/sciunto-org/python-bibtexparser/). It is not a wrapper to javascript and written in pure python, thus it differs considerably from the ris-translator and bibtex-translator, which is not really a good thing because original translator is quite robust. But this should give a good general idea on where to start.

Scripts provided here are used by the [Zotero Ancient Near East and Eastern Mediterranean Bibliography Group] (https://www.zotero.org/groups/ancient_near_east_and_eastern_mediterranean_multidisciplinary_group_a_collaborative_bibliography)
