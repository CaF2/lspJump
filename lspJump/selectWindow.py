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

import sys
import os
from gi.repository import Gtk, Gdk
from lspJump import settings
from lspJump.LspNavigator import LspNavigator

class TreeViewWithColumn(Gtk.TreeView):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for i, head in enumerate(['File', 'Line', '', '']):
			col = Gtk.TreeViewColumn(head, Gtk.CellRendererText(), text=i)
			self.append_column(col)
		col.set_visible(False)


class SelectWindow(Gtk.Window):
	def __init__(self, plugin, windowTitle, records, opener):
		Gtk.Window.__init__(self)
		self.plugin = plugin
		self.treeview = TreeViewWithColumn(
			model=Gtk.ListStore(str, int, int, str)
		)  # file, line, line_str
		self.treeview.set_rules_hint(True)
		self.connect("key-press-event", self.__enter)
		self.connect("button-press-event", self.__enter)
		sw = Gtk.ScrolledWindow()
		sw.add(self.treeview)
		for rec in records:
			if rec is not None:
				self.treeview.get_model().append(rec)
		self.add(sw)
		self.opener = opener
		self.set_title(windowTitle)
		self.set_size_request(700, 360)

	def __enter(self, w, e):
		event_type = e.get_event_type()
		if (
			event_type == Gdk.EventType._2BUTTON_PRESS
			or (
				event_type == Gdk.EventType.KEY_PRESS
				and e.keyval == 65293
			)
		):
			model, tree_iter = self.treeview.get_selection().get_selected()
			location = model.get(tree_iter, 0, 1, 2, 3)
			self.destroy()
			self.opener(location)
			
class ProjectDir(Gtk.Window):
	def __init__(self, plugin):
		Gtk.Window.__init__(self)

		settings_widget=SettingsWindow(plugin)
		self.add(settings_widget)
		
		self.set_size_request(700, 360)

class LanguageSettings(Gtk.Dialog):
	def __init__(self, parent,name,dialog_type):
		Gtk.Dialog.__init__(self,"My Dialog",parent.get_toplevel(),0,(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OK,Gtk.ResponseType.OK))
		
		box = self.get_content_area()
		
		label=Gtk.Label("Profile name:")
		box.add(label)
		
		self.name=Gtk.Entry()
		self.name.set_text(name)
		box.add(self.name)

		label=Gtk.Label("Lanuage names (comma separated):")
		box.add(label)
		
		self.lang_name=Gtk.Entry()
		self.lang_name.set_text(settings.LSP_LANGUAGES)
		box.add(self.lang_name)
		
		label=Gtk.Label("Path to the LSP server binary:")
		box.add(label)
		
		self.bin_entry=Gtk.Entry()
		self.bin_entry.set_text(settings.LSP_BIN)
		box.add(self.bin_entry)
		
		label=Gtk.Label("Language settings:")
		box.add(label)
		
		self.textview = Gtk.TextView()
		self.tbuffer=Gtk.TextBuffer()
		self.tbuffer.set_text(settings.LSP_SETTINGS)
		self.textview.set_buffer(self.tbuffer)
		box.add(self.textview)

		self.show_all()

		self.set_size_request(700, 360)

class SettingsWindow(Gtk.Grid):
	def __init__(self, plugin):
		Gtk.Grid.__init__(self)
		
		self.plugin = plugin

		self.set_column_homogeneous(True)
		
		row_num=0
		
		label=Gtk.Label("Project path:")
		self.attach(label, 0, row_num, 2, 1)
		row_num=row_num+1
		
		cb = Gtk.ComboBoxText()
		cb.connect("changed", self._click_histoy_path)
		path_histories = settings.SETTINGS_DATA.findall("path_history")
		for ppath in path_histories:
			if ppath.text is not None:
				cb.append_text(ppath.text)
		self.attach(cb, 0, row_num, 2, 1)
		row_num=row_num+1

		self.path_entry=Gtk.Entry()
		self.path_entry.set_text(settings.PROJECT_PATH)
		self.attach(self.path_entry, 0, row_num, 1, 1)
		
		button = Gtk.Button(label="Change")
		button.connect("clicked", self._change_project_path)
		self.attach(button, 1, row_num, 1, 1)
		row_num=row_num+1
		
		button_get_proj = Gtk.Button(label="Get project dir")
		button_get_proj.connect("clicked", self._get_proj)
		self.attach(button_get_proj, 0, row_num, 1, 1)
		row_num=row_num+1
		
		label=Gtk.Label("Profiles")
		self.attach(label, 0, row_num, 2, 1)
		row_num=row_num+1
		
		self.langugage_combo_pos=row_num
		row_num=row_num+1

		button_get_proj = Gtk.Button(label="New")
		button_get_proj.connect("clicked", self._new_language)
		self.attach(button_get_proj, 0, row_num, 1, 1)
		
		button_get_proj = Gtk.Button(label="Edit")
		button_get_proj.connect("clicked", self._edit_language)
		self.attach(button_get_proj, 1, row_num, 1, 1)
		
		row_num=row_num+1

		button_get_proj = Gtk.Button(label="Remove")
		button_get_proj.connect("clicked", self._remove_language)
		self.attach(button_get_proj, 0, row_num, 1, 1)

		button_get_proj = Gtk.Button(label="Set")
		button_get_proj.connect("clicked", self._set_language)
		self.attach(button_get_proj, 1, row_num, 1, 1)
		row_num=row_num+1
		
		self._generate_language_combo()
	def _generate_language_combo(self):
		if hasattr(self,"lang_cb"):
			self.lang_cb.destroy()
		self.lang_cb = Gtk.ComboBoxText()
		# cb.connect("changed", self.on_changed)
		language_settings = settings.SETTINGS_DATA.findall("language")
		index=0
		choosen_index=0
		for language_setting in language_settings:
			lang_name = language_setting.get("name")
			if lang_name is not None:
				self.lang_cb.append_text(lang_name)
				
				if settings.SETTINGS_LANGUAGE is not None:
					if lang_name==settings.SETTINGS_LANGUAGE.get("name"):
						choosen_index=index
				index=index+1
		self.lang_cb.set_active(choosen_index)
		self._set_language(None)
		self.attach(self.lang_cb, 0, self.langugage_combo_pos, 2, 1)
		self.lang_cb.show()
	def _change_project_path(self, w):
		new_path=self.path_entry.get_text()
		print("Changed to: "+new_path)
		settings.addPreviousPath(new_path)
		
		if settings.LSP_NAVIGATOR is not None:
			settings.LSP_NAVIGATOR.lsp_endpoint.shutdown()
			settings.LSP_NAVIGATOR.lsp_endpoint.send_notification("exit")
		settings.PROJECT_PATH=new_path
		settings.LSP_NAVIGATOR=LspNavigator()
		# settings.LSP_NAVIGATOR._initialize_project_path(settings.PROJECT_PATH)
	def _new_language(self, w):
		dialog=LanguageSettings(self,"",False)
		response=dialog.run()
		if response == Gtk.ResponseType.OK:
			print(dialog.lang_name.get_text())
			start,end=dialog.tbuffer.get_bounds()
			settings.setLspConfiguration(dialog.name.get_text(),dialog.lang_name.get_text(),dialog.bin_entry.get_text(),dialog.tbuffer.get_text(start,end,False),False)
		# 	print("The OK button was clicked")
		# elif response == Gtk.ResponseType.CANCEL:
		# 	print("The Cancel button was clicked")
		dialog.destroy()
		self._generate_language_combo()
	def _remove_language(self, w):
		profile_name=self.lang_cb.get_active_text()
		dialog = Gtk.MessageDialog(
			self.get_toplevel(),
			0,
			Gtk.MessageType.QUESTION,
			Gtk.ButtonsType.YES_NO,
			"Do you want to remove the language \""+profile_name+"\"",
		)
		# dialog.format_secondary_text("And this is the secondary text that explains things.")
		response = dialog.run()
		if response == Gtk.ResponseType.YES:
			print("QUESTION dialog closed by clicking YES button")
			settings.removeLanguage(profile_name)
		elif response == Gtk.ResponseType.NO:
			print("QUESTION dialog closed by clicking NO button")
		dialog.destroy()
		self._generate_language_combo()
	def _edit_language(self, w):
		profile_name=self.lang_cb.get_active_text()
		print("Editing::"+profile_name)
		settings.getSettings(profile_name)
		dialog=LanguageSettings(self,profile_name,False)
		response=dialog.run()
		if response == Gtk.ResponseType.OK:
			print(dialog.lang_name.get_text())
			start,end=dialog.tbuffer.get_bounds()
			settings.setLspConfiguration(dialog.name.get_text(),dialog.lang_name.get_text(),dialog.bin_entry.get_text(),dialog.tbuffer.get_text(start,end,False),True)
			print("The OK button was clicked")
		elif response == Gtk.ResponseType.CANCEL:
			print("The Cancel button was clicked")
		dialog.destroy()
		self._generate_language_combo()
	def _set_language(self, w):
		profile_name=self.lang_cb.get_active_text()
		print("Opening::"+profile_name)
		settings.getSettings(profile_name)
	def _get_proj(self, w):
		this_file_obj=self.plugin.window.get_active_document()
		this_file=this_file_obj.get_uri_for_display()
		print(os.path.dirname(this_file))
		self.path_entry.set_text(os.path.dirname(this_file))
	def _click_histoy_path(self, w):
		npath=w.get_active_text()
		self.path_entry.set_text(npath)
