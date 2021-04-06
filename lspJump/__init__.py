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

from collections import deque
from subprocess import CalledProcessError
import os

from gi.repository import GObject, Gedit, Gio
from gi.repository import PeasGtk

from lspJump import selectWindow, settings

def getCurrentIdentifier(doc):
	return doc.get_iter_at_mark(doc.get_insert())

ACTION_DEFS = [
	("lspJumpDef", "Go to definition", settings.keyJumpDef),
	("lspJumpRef", "Go to reference", settings.keyJumpRef),
	("lspJumpBack", "lspJump undo", settings.keyJumpBack),
	("lspJumpNext", "lspJump redo", settings.keyJumpNext),
	("lspJumpProjDir", "lspJump settings", settings.keyProjDir)
]


class lspJumpAppActivatable(GObject.Object, Gedit.AppActivatable):

	app = GObject.property(type=Gedit.App)

	def do_activate(self):
		#see https://gitlab.gnome.org/GNOME/gedit/-/blob/master/gedit/resources/gtk/menus-traditional.ui for the position
		self.menu_ext = self.extend_menu("search-section")
		for name, title, key in ACTION_DEFS:
			accelerator = "win." + name
			self.app.add_accelerator(key, accelerator, None)
			item = Gio.MenuItem.new(_(title), accelerator)
			self.menu_ext.append_menu_item(item)

	def do_deactivate(self):
		for action_def in ACTION_DEFS:
			accelerator = "win." + action_def[0]
			self.app.remove_accelerator(accelerator, None)
		self.menu_ext = None


class lspJumpWindowActivatable(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):
	__gtype_name = "lspJump"
	window = GObject.property(type=Gedit.Window)
	backstack = deque()
	nextstack = deque()

	def do_activate(self):
		slots = {
			"lspJumpDef": self.__jump_def,
			"lspJumpRef": self.__jump_ref,
			"lspJumpBack": self.__back,
			"lspJumpNext": self.__next,
			"lspJumpProjDir": self.__projdir
		}
		for name, title, key in ACTION_DEFS:
			action = Gio.SimpleAction(name=name)
			action.connect('activate', slots[name])
			self.window.add_action(action)

	def do_deactivate(self):
		for name, title, key in ACTION_DEFS:
			self.window.remove_action(name)

	def do_update_state(self):
		pass

	
	def do_create_configure_widget(self):
		return selectWindow.SettingsWindow(self);

	def __jump(self, navi_method):
		if settings.LSP_NAVIGATOR is not None:
			doc = self.window.get_active_document()
			identifier = getCurrentIdentifier(doc)
			refs = navi_method(settings.LSP_NAVIGATOR)(doc, identifier)
			self.add_history(self.backstack)
			self.jump(refs, identifier)
	
	def __jump_def(self, action, dummy):
		self.__jump(lambda navi: navi.getDefinitions)
	
	def __jump_ref(self, action, dummy):
		self.__jump(lambda navi: navi.getReferences)
	
	def __back(self, action, dummy):
		try:
			preLocation = self.backstack.pop()
		except IndexError:
			return
		self.add_history(self.nextstack)
		gio_file = Gio.File.new_for_path(preLocation[0].get_location().get_path())
		self.open_location(gio_file, preLocation[1])
	
	def __next(self, action, dummy):
		try:
			nextLocation = self.nextstack.pop()
		except IndexError:
			return
		self.add_history(self.backstack)
		gio_file = Gio.File.new_for_path(nextLocation[0].get_location().get_path())
		self.open_location(gio_file, nextLocation[1])
	
	def __projdir(self, action, dummy):
		window = selectWindow.ProjectDir(self)
		window.show_all()
	
	def jump(self, locations, identifier):
		"""
		locations: [(Gio.File, int)] or [(str, int), ...]
		"""
	
		if not locations:
			return
	
		def location_opener(location):
			path, line, code, doc_path = location
			if isinstance(path, Gio.File):
				gio_file = path
			else:
				dirname = os.path.dirname(doc_path)
				newpath = os.path.normpath(os.path.join(dirname, path))
				gio_file = Gio.File.new_for_path(newpath)
			self.open_location(gio_file, line)
	
		if len(locations) == 1:
			location_opener(locations[0])
		else:
			locations.sort()
			window = selectWindow.SelectWindow(self,"Item selection",locations,location_opener)
			window.show_all()

	def add_history(self, stack):
		doc = self.window.get_active_document()
		stack.append((
			doc.get_file(),
			doc.get_iter_at_mark(doc.get_insert()).get_line() + 1
		))
		if len(stack) == settings.historymax:
			stack.popleft()

	def open_location(self, location, line):
		for d in self.window.get_documents():
			d_location = d.get_file()
			doc_uri = d.get_file().get_location().get_path()
			if not d_location:
				continue
			if os.path.realpath(location.get_path())==doc_uri:
				tab = Gedit.Tab.get_from_document(d)
				self.window.set_active_tab(tab)
				d.goto_line(line - 1)
				self.window.get_active_view().scroll_to_cursor()
				break
		else:
			# file has not opened yet
			self.window.create_tab_from_location(
				location, None, line, 0, False, True
			)
