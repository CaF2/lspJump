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

from gi.repository import GObject, Gedit, Gio, Gtk, Gdk
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
			item = Gio.MenuItem.new(_(title)+" ("+key+")", accelerator)
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
	
	prev_buffer_coords = [0,0]
	hover_refs = ""

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
		self.window.connect('active-tab-changed', self.on_tab_changed)
	
	def do_deactivate(self):
		for name, title, key in ACTION_DEFS:
			self.window.remove_action(name)

	def do_update_state(self):
		pass

	def on_tab_changed(self, window):
		text_view = self.window.get_active_view()
		if text_view:
			# document_type=settings.get_window_programming_language_type(self.window)
			# print("DOCUMENT TYPE="+document_type)
			text_view.connect('query-tooltip', self.on_motion_notify_event_first)
			text_view.connect('key-press-event', self.on_tab_added)
			text_view.set_has_tooltip(True)
			# text_view.set_tooltip_text("Tooltip")

	def on_tab_added(self, widget, event):
		if event.state & Gdk.ModifierType.CONTROL_MASK and event.keyval == Gdk.KEY_e:
			text_view = self.window.get_active_view()
			doc = self.window.get_active_document()
			buffer = text_view.get_buffer()
			mark = buffer.get_insert()
			identifier = buffer.get_iter_at_mark(mark)
			marked_char=identifier.get_char()
			if marked_char!=' ' and marked_char!='\t':
				refs = settings.LSP_NAVIGATOR.getSuggestions(doc, identifier)
				items=refs['items']
				if len(items)>0:
					return self.show_suggestions(items,text_view)
		return False
	
	def show_suggestions(self, suggestions, text_view):
		# Logic to display suggestions
		dialog = Gtk.Dialog("Suggestions",self.window.get_toplevel(),0,(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OK,Gtk.ResponseType.OK))
		dialog.set_default_size(600, 400)
		# box = dialog.get_content_area()
		
		scrolled_window = Gtk.ScrolledWindow()
		scrolled_window.set_border_width(10)
		# box.add(scrolled_window)
		dialog.vbox.pack_start(scrolled_window, True, True, 0)
		
		listbox = Gtk.ListBox()
		scrolled_window.add(listbox)
		
		for suggestion in suggestions:
			print(suggestion)
			if "filterText" in suggestion:
				suggestion_btn = Gtk.Button(label=suggestion["filterText"])
				tooltip_text=""
				if "label" in suggestion:
					tooltip_text=suggestion["label"]
				if "documentation" in suggestion:
					if len(tooltip_text)>0:
						tooltip_text=tooltip_text+"\n=====\n"
					tooltip_text=tooltip_text+str(suggestion["documentation"])
				if "textEdit" in suggestion and "newText" in suggestion["textEdit"]:
					if len(tooltip_text)>0:
						tooltip_text=tooltip_text+"\n=====\n"
					tooltip_text=tooltip_text+suggestion["textEdit"]["newText"]
				suggestion_btn.set_tooltip_text(tooltip_text)
				suggestion_btn.suggestion=suggestion
				suggestion_btn.text_view=text_view
				suggestion_btn.dialog=dialog
				suggestion_btn.connect("clicked", self.change_to_suggestion)
				listbox.add(suggestion_btn)
		dialog.show_all()
		
		# dialog.format_secondary_text("\n".join(suggestions))
		dialog.run()
		dialog.destroy()
		return True
	
	def replace_text(self, textview, start_line, start_column, end_line, end_column, new_text):
		#needs improvement, work like the snippet extension and jump around in the inserted text with tab?
		if new_text.endswith("$0"):
			new_text=new_text[:-2]
		
		buffer = textview.get_buffer()
		start_iter = buffer.get_iter_at_line_index(start_line, start_column)
		end_iter = buffer.get_iter_at_line_index(end_line, end_column)
		text = buffer.get_text(start_iter, end_iter, False)
		min_length = min(len(text), len(new_text))
		
		first_diff_char=len(text)
		found_diff=False
		
		for i in range(min_length):
			if text[i] != new_text[i]:
				first_diff_char=i
				found_diff=True
		
		if found_diff:
			buffer.delete(start_iter, end_iter)
			buffer.insert(start_iter, new_text)
		else:
			buffer.insert(end_iter, new_text[first_diff_char:])
	
	def change_to_suggestion(self, widget):
		suggestion=widget.suggestion
		text_view=widget.text_view
		# print("SUGGESTION")
		# print(suggestion)
		start_line=suggestion["textEdit"]["range"]["start"]["line"]
		start_character=suggestion["textEdit"]["range"]["start"]["character"]
		end_line=suggestion["textEdit"]["range"]["end"]["line"]
		#add one for the added tab
		end_character=suggestion["textEdit"]["range"]["end"]["character"]
		text_replacement=suggestion["textEdit"]["newText"]
		self.replace_text(text_view,start_line, start_character, end_line, end_character, text_replacement)
		widget.dialog.destroy()
	def on_motion_notify_event_first(self, textview, x, y, keyboard_mode, tooltip):
		textview.disconnect_by_func(self.on_motion_notify_event_first)
		doctype=settings.get_window_programming_language_type(self.window)
		is_supported=settings.get_if_supported_language_type(doctype,False)
		
		if is_supported:
			textview.connect('query-tooltip', self.on_motion_notify_event)
	
	def is_not_inside_prev_buff_range(self, prev_buf, buf):
		box_size=2
		# print(str(buf[0])+","+str(prev_buf[0])+","+str(buf[1])+","+str(prev_buf[1]))
		if (buf[0]>prev_buf[0]+box_size or buf[0]<prev_buf[0]-box_size) or (buf[1]>prev_buf[1]+box_size or buf[1]<prev_buf[1]-box_size):
			return True
		return False
	
	def on_motion_notify_event(self, textview, x, y, keyboard_mode, tooltip):
		additional=""
		if settings.LSP_NAVIGATOR is not None:
			doc = self.window.get_active_document()
			buffer_coords = textview.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, x, y)
			[obj,identifier] = textview.get_iter_at_location(buffer_coords[0], buffer_coords[1])
			marked_char=identifier.get_char()
			if marked_char!=' ' and marked_char!='\t':
				if self.is_not_inside_prev_buff_range(self.prev_buffer_coords,buffer_coords):
					# print("GET NEW")
					self.hover_refs = settings.LSP_NAVIGATOR.getHover(doc, identifier)
					self.prev_buffer_coords=buffer_coords
				if self.hover_refs is None:
					#"query-tooltip"
					textview.disconnect_by_func(self.on_motion_notify_event)
				if self.hover_refs and "contents" in self.hover_refs:
					for c_obj in self.hover_refs["contents"]:
						if len(additional)>0:
							additional=additional+"\n======\n"
						if type(c_obj) == str:
							additional= additional+c_obj
						else:
							additional= additional+c_obj["value"]
		if len(additional)>0:
			tooltip.set_text(additional)
			return True
		else:
			return False
		
	
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
		self.open_location(gio_file, preLocation[1], preLocation[2])
	
	def __next(self, action, dummy):
		try:
			nextLocation = self.nextstack.pop()
		except IndexError:
			return
		self.add_history(self.backstack)
		gio_file = Gio.File.new_for_path(nextLocation[0].get_location().get_path())
		self.open_location(gio_file, nextLocation[1], nextLocation[2])
	
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
			self.open_location(gio_file, line, code)
	
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
			doc.get_iter_at_mark(doc.get_insert()).get_line() + 1,
			doc.get_iter_at_mark(doc.get_insert()).get_line_offset() + 1
		))
		if len(stack) == settings.historymax:
			stack.popleft()

	def open_location(self, location, line, column):
		for d in self.window.get_documents():
			d_location = d.get_file()
			doc_uri = d.get_file().get_location().get_path()
			if not d_location:
				continue
			if os.path.realpath(location.get_path())==doc_uri:
				tab = Gedit.Tab.get_from_document(d)
				self.window.set_active_tab(tab)
				piter=d.get_iter_at_line_index(line - 1,column - 1)
				d.place_cursor(piter)
				self.window.get_active_view().scroll_to_iter(piter,0.25,False,0,0)
				break
		else:
			tab=self.window.create_tab(True)
			tab.load_file(location, None, line, column, False)

