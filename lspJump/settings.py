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
SETTINGS_DATA = None
#current language structure
SETTINGS_LANGUAGE = None

LSP_LANGUAGES = "c"
LSP_BIN = "/usr/bin/ccls"
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

keyJumpDef = "F3"
keyJumpRef = "F4"
keyJumpBack = "<Alt>b"
keyJumpNext = "<Alt><Shift>b"
keyProjDir = "F5"

historymax = 100

LSP_NAVIGATOR=None

#########

def getSettings(profilename):
	global LSP_BIN
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
				if languages is not None:
					SETTINGS_LANGUAGE=languages[0]
					lsp_bins = SETTINGS_LANGUAGE.findall("lsp_bin")
					if lsp_bins is not None:
						LSP_BIN = lsp_bins[0].text
					lsp_language = SETTINGS_LANGUAGE.findall("lsp_language")
					if lsp_language is not None:
						LSP_LANGUAGES = lsp_language[0].text
					lsp_settings = SETTINGS_LANGUAGE.findall("lsp_settings")
					if lsp_settings is not None:
						LSP_SETTINGS = lsp_settings[0].text

def setLspConfiguration(name,language,path,settings,overwrite=True):
	global LSP_BIN
	global LSP_SETTINGS
	global LSP_LANGUAGES

	global SETTINGS_DATA
	global SETTINGS_LANGUAGE

	LSP_BIN = path
	LSP_SETTINGS = settings
	LSP_LANGUAGES = language
	
	if SETTINGS_DATA is None:
		SETTINGS_DATA = ET.Element('data')
	
	lsp_language_exists=True
	lsp_language=None
	lsp_bin_exists=True
	lsp_bin=None
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
		
		lsp_pre_settings=SETTINGS_LANGUAGE.findall("lsp_settings")
		try:
			lsp_settings = lsp_pre_settings[0]
		except IndexError:
			lsp_settings_exists=False
	else:
		SETTINGS_LANGUAGE = ET.SubElement(SETTINGS_DATA, 'language')
		lsp_language_exists=False
		lsp_bin_exists=False
		lsp_settings_exists=False
	
	SETTINGS_LANGUAGE.set("name",name)
	
	if lsp_language_exists is False:
		lsp_language = ET.SubElement(SETTINGS_LANGUAGE, 'lsp_language')
	lsp_language.text = LSP_LANGUAGES
	if lsp_bin_exists is False:
		lsp_bin = ET.SubElement(SETTINGS_LANGUAGE, 'lsp_bin')
	lsp_bin.text = LSP_BIN
	if lsp_settings_exists is False:
		lsp_settings = ET.SubElement(SETTINGS_LANGUAGE, 'lsp_settings')
	lsp_settings.text = LSP_SETTINGS

	mydata = ET.tostring(SETTINGS_DATA)
	myfile = open(SETTINGS_FILE, "wb")
	myfile.write(mydata)

def addPreviousPath(path):
	global SETTINGS_DATA
	add_val=True
	path_histories = SETTINGS_DATA.findall("path_history")
	for ppath in path_histories:
		if ppath.text is not None and ppath.text==path:
			add_val=False
			break
	if add_val:
		ppath = ET.SubElement(SETTINGS_DATA, 'path_history')
		ppath.text=path

getSettings(None)
