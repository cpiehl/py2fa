#!/usr/bin/env python2
import os, sys
import json
import hmac, base64, struct, hashlib, time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject


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


	def add_account_dialog( self, button ):

		def on_ok_clicked( widget, name_entry, secret_entry ):
			name = name_entry.get_text()
			secret = secret_entry.get_text().replace(" ", "")
			if self.add_account( name, secret ) == True:
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

			vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

			label1 = Gtk.Label(xalign=0)
			label1.set_markup("<big>" + otp_code[:3] + " " + otp_code[3:] + "</big>")
			label2 = Gtk.Label(name, xalign=0)
			vbox.pack_start(label1, True, True, 0)
			vbox.pack_start(label2, True, True, 0)

			self.listbox.add(vbox)
			vbox.show_all()

			return True


	def update_otps( self, user_data ):
		for child in self.listbox.get_children():
			child.destroy()
		self.load(accountsList=self.accounts)

		runat = int(time.time()+30)//30*30
		GObject.timeout_add(1000 * (runat - time.time()), self.update_otps, None)

		self.progressbar_reset = True

		return False  # Don't auto-continue


	def update_progress( self, user_data ):
		if self.progressbar_reset == True:
			self.progressbar_fraction = 1
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

		for name, secret in accountsList.iteritems():
			self.add_account( name, secret )


	def main_quit( self, event, user_data ):
		self.save()     # Save everything
		Gtk.main_quit() # Quit


win = OTPWindow()
win.connect("delete-event", win.main_quit)
win.show_all()
win.load()
Gtk.main()
