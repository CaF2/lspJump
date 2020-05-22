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
	

class SettingsWindow(Gtk.Grid):
	def __init__(self, plugin):
		Gtk.Grid.__init__(self)
		
		self.plugin = plugin
		
		self.set_column_homogeneous(True)
		
		row_num=0
		
		label=Gtk.Label("Project path:")
		self.attach(label, 0, row_num, 1, 1)
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
		
		label=Gtk.Label("Path to the LSP server binary:")
		self.attach(label, 0, row_num, 1, 1)
		row_num=row_num+1
		
		self.bin_entry=Gtk.Entry()
		self.bin_entry.set_text(settings.LSP_BIN)
		self.attach(self.bin_entry, 0, row_num, 1, 1)
		
		button = Gtk.Button(label="Change")
		button.connect("clicked", self._change_binary)
		self.attach(button, 1, row_num, 1, 1)
		
	def _change_project_path(self, w):
		print(self.path_entry.get_text())
		
		if settings.LSP_NAVIGATOR is not None:
			settings.LSP_NAVIGATOR.lsp_endpoint.shutdown()
			settings.LSP_NAVIGATOR.lsp_endpoint.send_notification("exit")
		settings.PROJECT_PATH=self.path_entry.get_text()
		settings.LSP_NAVIGATOR=LspNavigator()
		# settings.LSP_NAVIGATOR._initialize_project_path(settings.PROJECT_PATH)
	def _get_proj(self, w):
		this_file_obj=self.plugin.window.get_active_document()
		this_file=this_file_obj.get_uri_for_display()
		print(os.path.dirname(this_file))
		self.path_entry.set_text(os.path.dirname(this_file))
	def _change_binary(self, w):
		print(self.bin_entry.get_text())
		settings.setLspBin(self.bin_entry.get_text())
