#	lspJump - a gedit plugin to browse code using the LSP protocol
#	Copyright (C) 2020  Florian Evaldsson

#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.

#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.

#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.

from lspJump.LspNavigator import LspNavigator
import xml.etree.ElementTree as ET
import os

#########

SETTINGS_FILE = os.path.dirname(os.path.realpath(__file__))+"settings.xml"
#root of xml
SETTINGS_DATA = None
#current language structure
SETTINGS_LANGUAGE = None

LSP_LANGUAGES = "C,C++"
LSP_BIN = "/usr/bin/ccls"
LSP_BIN_ARGS = ""
LSP_SEARCH_PATH = "compile_commands.json"
LSP_SETTINGS = """{
	"textDocument": {"codeAction": {"dynamicRegistration": true},
	"codeLens": {"dynamicRegistration": true},
	"colorProvider": {"dynamicRegistration": true},
	"completion": {"completionItem": {"commitCharactersSupport": true,"documentationFormat": ["markdown", "plaintext"],"snippetSupport": true},
	"completionItemKind": {"valueSet": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25]},
	"contextSupport": true,
	"dynamicRegistration": true},
	"definition": {"dynamicRegistration": true},
	"documentHighlight": {"dynamicRegistration": true},
	"documentLink": {"dynamicRegistration": true},
	"documentSymbol": {"dynamicRegistration": true,
	"symbolKind": {"valueSet": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26]}},
	"formatting": {"dynamicRegistration": true},
	"hover": {"contentFormat": ["markdown", "plaintext"],
	"dynamicRegistration": true},
	"implementation": {"dynamicRegistration": true},
	"onTypeFormatting": {"dynamicRegistration": true},
	"publishDiagnostics": {"relatedInformation": true},
	"rangeFormatting": {"dynamicRegistration": true},
	"references": {"dynamicRegistration": true},
	"rename": {"dynamicRegistration": true},
	"signatureHelp": {"dynamicRegistration": true,
	"signatureInformation": {"documentationFormat": ["markdown", "plaintext"]}},
	"synchronization": {"didSave": true,
	"dynamicRegistration": true,
	"willSave": true,
	"willSaveWaitUntil": true},
	"typeDefinition": {"dynamicRegistration": true}},
	"workspace": {"applyEdit": true,
	"configuration": true,
	"didChangeConfiguration": {"dynamicRegistration": true},
	"didChangeWatchedFiles": {"dynamicRegistration": true},
	"executeCommand": {"dynamicRegistration": true},
	"symbol": {"dynamicRegistration": true,
	"symbolKind": {"valueSet": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26]}},"workspaceEdit": {"documentChanges": true},
	"workspaceFolders": true}
}"""

PROJECT_PATH = ''
MAX_SAVE_PATH = 20

keyJumpDef = "F3"
keyJumpRef = "F4"
keyJumpBack = "<Alt>u"
keyJumpNext = "<Alt><Shift>u"
keyProjDir = "F5"

historymax = 100

LSP_NAVIGATOR=None

DEBUG = os.getenv("DEBUG", "").lower() in ["true", "1"]
DEVELOP_FEATURES = os.getenv("DEVELOP_FEATURES", "").lower() in ["true", "1"]

#########

def get_document_programming_language_type(doc):
	if doc:
		# Get the MIME type of the document
		language=doc.get_language()
		if language:
			mime_type=language.get_name()
			#mime_type = doc.get_mime_type()
			return mime_type
	return None
	
def get_window_programming_language_type(window):
	# Get the active view and document
	view = window.get_active_view()
	if view:
		doc = view.get_buffer()
		return get_document_programming_language_type(doc)
	return None

def get_if_supported_language_type(doctype,print_on_fail):
	global LSP_LANGUAGES
	doctype_lower=doctype.lower()
	supported_languages=LSP_LANGUAGES.lower().split(',')
	
	if doctype_lower in supported_languages:
		return True
	elif print_on_fail:
		print("DOCTYPE="+doctype_lower+" SUPPORTED LANGUAGES="+str(supported_languages))
	return False

def getValueFromSettings(obj,attr,def_val):
	lsp_searchs = obj.findall(attr)
	if lsp_searchs is not None and len(lsp_searchs)>0:
		if lsp_searchs[0].text is not None and len(lsp_searchs[0].text)>0:
			return lsp_searchs[0].text
	return def_val

def getSettings(profilename):
	global LSP_BIN
	global LSP_BIN_ARGS
	global LSP_SEARCH_PATH
	global LSP_SETTINGS
	global LSP_LANGUAGES
	
	global SETTINGS_DATA
	global SETTINGS_LANGUAGE
	
	if os.path.exists(SETTINGS_FILE):
		tree = ET.parse(SETTINGS_FILE)
		if tree is not None:
			SETTINGS_DATA = tree.getroot()
			if SETTINGS_DATA is not None:
				additional=""
				if profilename is not None:
					additional="[@name='"+profilename+"']"
				languages = SETTINGS_DATA.findall("language"+additional)
				if languages is not None and len(languages)>0:
					SETTINGS_LANGUAGE=languages[0]
					LSP_BIN = getValueFromSettings(SETTINGS_LANGUAGE,"lsp_bin","")
					LSP_BIN_ARGS = getValueFromSettings(SETTINGS_LANGUAGE,"lsp_bin_args","")
					LSP_SEARCH_PATH = getValueFromSettings(SETTINGS_LANGUAGE,"lsp_search","")
					LSP_LANGUAGES = getValueFromSettings(SETTINGS_LANGUAGE,"lsp_language","")
					LSP_SETTINGS = getValueFromSettings(SETTINGS_LANGUAGE,"lsp_settings","{}")

def setLspConfiguration(name,language,path,args,search_file,settings,overwrite=True):
	global LSP_BIN
	global LSP_BIN_ARGS
	global LSP_SEARCH_PATH
	global LSP_SETTINGS
	global LSP_LANGUAGES

	global SETTINGS_DATA
	global SETTINGS_LANGUAGE
	
	if path is not None and len(path)>0:
		LSP_BIN = path
	if args is not None and len(args)>0:
		LSP_BIN_ARGS = args
	if search_file is not None and len(search_file)>0:
		LSP_SEARCH_PATH = search_file
	if settings is not None and len(settings)>0:
		LSP_SETTINGS = settings
	if language is not None and len(language)>0:
		LSP_LANGUAGES = language
	
	if SETTINGS_DATA is None:
		SETTINGS_DATA = ET.Element('data')
	
	lsp_language_exists=True
	lsp_language=None
	lsp_bin_exists=True
	lsp_bin=None
	lsp_bin_args_exists=True
	lsp_bin_args=None
	lsp_search_exists=True
	lsp_search=None
	lsp_settings_exists=True
	lsp_settings=None

	if SETTINGS_LANGUAGE is not None and overwrite is True:
		lsp_pre_language=SETTINGS_LANGUAGE.findall("lsp_language")
		try:
			lsp_language = lsp_pre_language[0]
		except IndexError:
			lsp_language_exists=False

		lsp_pre_bin=SETTINGS_LANGUAGE.findall("lsp_bin")
		try:
			lsp_bin = lsp_pre_bin[0]
		except IndexError:
			lsp_bin_exists=False
			
		lsp_pre_bin_args=SETTINGS_LANGUAGE.findall("lsp_bin_args")
		try:
			lsp_bin_args = lsp_pre_bin_args[0]
		except IndexError:
			lsp_bin_args_exists=False
		
		lsp_pre_search=SETTINGS_LANGUAGE.findall("lsp_search")
		try:
			lsp_search = lsp_pre_search[0]
		except IndexError:
			lsp_search_exists=False
		
		lsp_pre_settings=SETTINGS_LANGUAGE.findall("lsp_settings")
		try:
			lsp_settings = lsp_pre_settings[0]
		except IndexError:
			lsp_settings_exists=False
	else:
		SETTINGS_LANGUAGE = ET.SubElement(SETTINGS_DATA, 'language')
		lsp_language_exists=False
		lsp_bin_exists=False
		lsp_bin_args_exists=False
		lsp_search_exists=False
		lsp_settings_exists=False
	
	SETTINGS_LANGUAGE.set("name",name)
	
	if lsp_language_exists is False:
		lsp_language = ET.SubElement(SETTINGS_LANGUAGE, 'lsp_language')
	lsp_language.text = LSP_LANGUAGES
	if lsp_bin_exists is False:
		lsp_bin = ET.SubElement(SETTINGS_LANGUAGE, 'lsp_bin')
	lsp_bin.text = LSP_BIN
	if lsp_bin_args_exists is False:
		lsp_bin_args = ET.SubElement(SETTINGS_LANGUAGE, 'lsp_bin_args')
	lsp_bin_args.text = LSP_BIN_ARGS
	if lsp_search_exists is False:
		lsp_search = ET.SubElement(SETTINGS_LANGUAGE, 'lsp_search')
	lsp_search.text = LSP_SEARCH_PATH
	if lsp_settings_exists is False:
		lsp_settings = ET.SubElement(SETTINGS_LANGUAGE, 'lsp_settings')
	lsp_settings.text = LSP_SETTINGS
	write_settings_data()

def write_settings_data():
	if SETTINGS_DATA is not None:
		mydata = ET.tostring(SETTINGS_DATA)
		myfile = open(SETTINGS_FILE, "wb")
		myfile.write(mydata)

def addPreviousPath(path):
	global SETTINGS_DATA
	global MAX_SAVE_PATH
	if SETTINGS_DATA is None:
		SETTINGS_DATA = ET.Element('data')
	add_val=True
	path_histories = SETTINGS_DATA.findall("path_history")

	for ppath in path_histories:
		if ppath.text is not None and ppath.text==path:
			add_val=False
			break
	if add_val:
		if len(path_histories)>MAX_SAVE_PATH:
			SETTINGS_DATA.remove(path_histories[0])
		ppath = ET.SubElement(SETTINGS_DATA, 'path_history')
		ppath.text=path
	write_settings_data()

def removeLanguage(languagename):
	if SETTINGS_DATA is not None:
		languages = SETTINGS_DATA.findall("language[@name='"+languagename+"']")
		if languages is not None:
			SETTINGS_DATA.remove(languages[0])
	write_settings_data()

def debugprint(msg):
	if DEBUG:
		print(msg)

getSettings(None)
