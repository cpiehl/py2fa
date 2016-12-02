#!/usr/bin/env python2
import os, sys
import json
import hmac, base64, struct, hashlib, time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject

UI_INFO = """
<ui>
  <popup name='ContextMenu'>
    <menuitem action='ContextRemove' />
  </popup>
</ui>
"""


def fullpath( relpath ):
	return os.path.join(os.path.dirname(__file__), relpath)


def get_hotp_token(secret, intervals_no):
	"""
		Counter-based OTP
	"""
	key = base64.b32decode(secret, True)
	msg = struct.pack(">Q", intervals_no)
	h = hmac.new(key, msg, hashlib.sha1).digest()
	o = ord(h[19]) & 15
	h = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
	return h


def get_totp_token(secret):
	"""
		Timer-based OTP
	"""
	secret = secret.replace(" ", "")
	secret += '=' * (-len(secret) % 8)  # Add correct '=' padding
	return get_hotp_token(secret, intervals_no=int(time.time())//30)


class OTPWindow(Gtk.Window):

	def __init__(self):
		Gtk.Window.__init__(self, title="Py2FA")

		self.set_default_size(200, 300)
		self.progressbar_fraction = 1
		self.progressbar_reset = False # Progress bar semaphore

		# Right click remove -> confirm menu
		self.popup = Gtk.Menu()
		menuitem_edit = Gtk.MenuItem("Edit")
		self.popup.append(menuitem_edit)
		self.popup.append(Gtk.SeparatorMenuItem())
		menuitem_remove = Gtk.MenuItem("Remove")
		self.popup.append(menuitem_remove)
		submenu = Gtk.Menu()
		menuitem_confirm = Gtk.MenuItem("Confirm")
		submenu.append(menuitem_confirm)
		menuitem_remove.set_submenu(submenu)
		menuitem_confirm.connect("button-release-event", self.remove_account)
		menuitem_edit.connect("button-release-event", self.edit_account_dialog)
		self.popup.show_all()

		# I don't know how to retrieve this from the MenuItem callback,
		# so save it in this "global" string in show_context_menu() to be
		# used in remove_account()
		self.selected_account_name = None

		box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		self.add(box_outer)

		self.listbox = Gtk.ListBox()
		self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
		box_outer.pack_start(self.listbox, True, True, 0)

		self.progressbar = Gtk.ProgressBar()
		box_outer.pack_start(self.progressbar, False, False, 0)

		button = Gtk.Button.new_with_label("Add")
		button.connect("clicked", self.add_account_dialog)
		box_outer.pack_start(button, False, False, 0)

		self.accounts = {}

		runat = int(time.time()+30)//30*30
		GObject.timeout_add(1000 * (runat - time.time()), self.update_otps, None)

		runat = int(time.time() + 1) + 0.5
		GObject.timeout_add(1000 * (runat - time.time()), self.update_progress, None)

		self.progressbar_fraction -= (int(time.time())%30)/30.0
		self.progressbar.set_fraction(self.progressbar_fraction)


	def show_context_menu( self, widget, event ):
		"""
			Right click menu for edit/remove
		"""
		if event.button == 3: # right click
			# hopefully always the clicked entry's name
			self.selected_account_name = widget.get_children()[0].get_children()[1].get_text()
			self.popup.popup(None, None, None, None, event.button, event.time)
			return True # event has been handled


	def add_account_dialog( self, button ):

		def on_ok_clicked( widget, name_entry, secret_entry ):
			name = name_entry.get_text()
			secret = secret_entry.get_text().replace(" ", "")
			if name in self.accounts:
				self.add_message.set_markup('<span color="red">Unique Name Required</span>')
			elif self.add_account( name, secret ) == True:
				self.save()  # Save this new entry
				dialog.destroy()
			else:
				self.add_message.set_markup('<span color="red">Invalid Secret</span>')


		def on_cancel_clicked( widget ):
			dialog.destroy()


		dialog = Gtk.Window(title="Add Account")

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		dialog.add(vbox)

		name_entry = Gtk.Entry()
		name_entry.set_text("Name")
		vbox.pack_start(name_entry, True, True, 0)

		secret_entry = Gtk.Entry()
		secret_entry.set_text("Secret")
		vbox.pack_start(secret_entry, True, True, 0)

		self.add_message = Gtk.Label(xalign=0)
		vbox.pack_start(self.add_message, True, True, 0)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
		vbox.pack_start(hbox, False, False, 0)

		button_ok = Gtk.Button("Add")
		button_ok.connect("clicked", on_ok_clicked, name_entry, secret_entry)
		hbox.pack_start(button_ok, True, True, 0)

		button_cancel = Gtk.Button("Cancel")
		button_cancel.connect("clicked", on_cancel_clicked)
		hbox.pack_start(button_cancel, True, True, 0)

		dialog.show_all()


	def edit_account_dialog( self, widget, event ):

		def on_ok_clicked( widget, name_entry, secret_entry ):
			name = name_entry.get_text()
			secret = secret_entry.get_text().replace(" ", "")
			if name != self.selected_account_name and name in self.accounts:
				self.add_message.set_markup('<span color="red">Unique Name Required</span>')
			elif self.edit_account( name, secret ) == True:
				self.save()  # Save this new entry
				dialog.destroy()
				self.selected_account_name = None
			else:
				self.add_message.set_markup('<span color="red">Invalid Secret</span>')


		def on_cancel_clicked( widget ):
			dialog.destroy()
			self.selected_account_name = None


		dialog = Gtk.Window(title="Edit Account")

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		dialog.add(vbox)

		name_entry = Gtk.Entry()
		name_entry.set_text(self.selected_account_name)
		vbox.pack_start(name_entry, True, True, 0)

		secret_entry = Gtk.Entry()
		secret_entry.set_text(self.accounts[self.selected_account_name])
		vbox.pack_start(secret_entry, True, True, 0)

		self.add_message = Gtk.Label(xalign=0)
		vbox.pack_start(self.add_message, True, True, 0)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
		vbox.pack_start(hbox, False, False, 0)

		button_ok = Gtk.Button("Save")
		button_ok.connect("clicked", on_ok_clicked, name_entry, secret_entry)
		hbox.pack_start(button_ok, True, True, 0)

		button_cancel = Gtk.Button("Cancel")
		button_cancel.connect("clicked", on_cancel_clicked)
		hbox.pack_start(button_cancel, True, True, 0)

		dialog.show_all()


	def add_account( self, name, secret ):
		"""
			Add a new account and update the UI
		"""
		try:
			otp_code = str(get_totp_token(secret)).zfill(6)
		except TypeError:
			return False
		else:
			if name not in self.accounts:
				self.accounts[name] = secret

			ebox = Gtk.EventBox()
			vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

			label1 = Gtk.Label(xalign=0)
			label1.set_markup("<big>" + otp_code[:3] + " " + otp_code[3:] + "</big>")
			label2 = Gtk.Label(name, xalign=0)
			vbox.pack_start(label1, True, True, 0)
			vbox.pack_start(label2, True, True, 0)

			ebox.connect("button-release-event", self.show_context_menu)

			ebox.add(vbox)
			self.listbox.add(ebox)
			ebox.show_all()

			return True


	def edit_account( self, name, secret ):
		"""
			Edit and account and update the UI
		"""
		try:
			otp_code = str(get_totp_token(secret)).zfill(6)
		except TypeError:
			return False
		else:
			if name != self.selected_account_name and name not in self.accounts:
				self.accounts[name] = secret
				del self.accounts[self.selected_account_name]
				self.update_otps(None)

			return True


	def remove_account( self, menuitem, eventbutton ):
		"""
			Remove account by name and reload UI
		"""
		if self.selected_account_name in self.accounts:
			del self.accounts[self.selected_account_name]
			self.selected_account_name = None
			self.update_otps(None)
			self.save()


	def update_otps( self, user_data ):
		"""
			Remove all accounts' UI elements and reload with new OTPs
		"""
		for child in self.listbox.get_children():
			child.destroy()
		self.load(accountsList=self.accounts)

		runat = int(time.time()+30)//30*30
		GObject.timeout_add(1000 * (runat - time.time()), self.update_otps, None)

		self.progressbar_reset = True

		return False  # Don't auto-continue


	def update_progress( self, user_data ):
		"""
			Decrement the progress bar and start a new timer
		"""
		print self.selected_account_name
		if self.progressbar_reset == True:
			self.progressbar_fraction = 1 - (int(time.time())%30)/30.0
			self.progressbar.set_fraction(self.progressbar_fraction)
			self.progressbar_reset = False
		else:
			self.progressbar_fraction -= 0.0333
			self.progressbar.set_fraction(self.progressbar_fraction)

		runat = int(time.time() + 1) + 0.5
		GObject.timeout_add(1000 * (runat - time.time()), self.update_progress, None)

		return False  # Don't auto-continue


	def save( self ):

		"""
			Save any data to a file (the links/etc)
		"""
		width,height = self.get_size()
		saveJsonText = json.dumps( {
			'accounts': self.accounts,
			'resHeight': height,
			'resWidth': width
		}, sort_keys=True )

		with open( fullpath( 'py2fa.json' ), 'wb' ) as f:
			f.write( saveJsonText )


	def load( self, accountsList=None ):

		"""
			Load any saved data
		"""

		if accountsList is None:
			try:
				file = open( fullpath( 'py2fa.json' ), 'rb' )
			except IOError:
				return

			data = json.loads( file.read() )
			accountsList = data['accounts']

			try:
				resWidth = data['resWidth']
				resHeight = data['resHeight']
			except KeyError:
				resWidth = 200
				resHeight = 300

			file.close()

			self.resize( resWidth, resHeight )

		for name, secret in sorted(accountsList.iteritems()):
			self.add_account( name, secret )


	def main_quit( self, event, user_data ):
		self.save()     # Save everything
		Gtk.main_quit() # Quit


win = OTPWindow()
win.connect("delete-event", win.main_quit)
win.show_all()
win.load()
Gtk.main()
