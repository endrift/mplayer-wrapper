#!/usr/bin/env python2
import pygtk
pygtk.require('2.0')
import gtk
import gobject

import os
import select
import subprocess

class RootWindow(object):
	def  __init__(self):
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect('delete_event', self.quit)
		self.window.set_title('Media Player')
		table = gtk.Table(2, 2, False)
		self.window.add(table)
		extButton = gtk.Button('External Drive')
		extButton.connect('clicked', lambda w: self.selectFile('/'))
		ytButton = gtk.Button('YouTube Video')
		ytButton.connect('clicked', lambda w: self.selectYouTube())
		remoteButton = gtk.Button('Remote Filesystem')
		frameBox = gtk.VBox(True, 0)
		frameBox.pack_start(extButton)
		frameBox.pack_start(ytButton)
		frameBox.pack_start(remoteButton)
		table.attach(frameBox, 0, 1, 0, 1)
		self.playlist = PlaylistWidget()
		table.attach(self.playlist.widget, 1, 2, 0, 2)

		controlPad = gtk.Table(1, 1, False)
		table.attach(controlPad, 0, 1, 1, 2)
		playButton = gtk.Button();
		playArrow = gtk.Arrow(gtk.ARROW_RIGHT, gtk.SHADOW_ETCHED_IN)
		playButton.add(playArrow)
		playButton.set_border_width(0)
		playButton.connect('clicked', self.play)
		controlPad.attach(playButton, 0, 1, 0, 1)
		self.window.show_all()

	def selectDrive(self):
		pass

	def selectFile(self, root):
		f = gtk.FileChooserDialog('Select File', None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		f.set_default_response(gtk.RESPONSE_CANCEL)
		f.set_select_multiple(True)
		f.set_current_folder(root)
		response = f.run()
		if response == gtk.RESPONSE_OK:
			self.playlist.addItems([LocalFile(name) for name in f.get_filenames()])
		f.destroy()

	def selectYouTube(self):
		ytWindow = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, None)
		ytWindow.set_markup('Enter URL')
		ytWindow.connect('delete_event', lambda w,d: w.destroy())
		ytWindow.set_default_response(gtk.RESPONSE_CANCEL)
		inputBox = gtk.Entry()
		ytWindow.vbox.pack_start(inputBox)
		ytWindow.show_all()
		response = ytWindow.run()
		if response == gtk.RESPONSE_OK:
			try:
				self.playlist.addItem(YouTubeMovie(inputBox.get_text()))
			except:
				pass
		ytWindow.destroy()

	def play(self, widget):
		p = self.playlist.compile()
		if p:
			p.play()
		else:
			error = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, None)
			error.set_markup('Cannot play empty playlist!')
			error.run()
			error.destroy()

	def quit(self, widget, event, data=None):
		gtk.main_quit()
		return False

class LocalFile(object):
	def __init__(self, filename):
		self.filename = filename

	def __repr__(self):
		return self.filename

	def uri(self):
		return self.filename

class YouTubeMovie(object):
	def __init__(self, url):
		self.url = url
		self.title = url

	def __repr__(self):
		return 'YouTube: {}'.format(self.title)

	def uri(self):
		return subprocess.check_output(['youtube-dl', '-g', self.url])

class PlaylistWidget(object):
	def __init__(self):
		def format_data(col, cell, model, iter):
			obj = model.get_value(iter, 0)
			cell.set_property('text', repr(obj))

		self.listStore = gtk.ListStore(object)
		nameText = gtk.CellRendererText()
		nameCol = gtk.TreeViewColumn('Name', nameText)
		nameCol.set_cell_data_func(nameText, format_data)
		self.widget = gtk.TreeView(self.listStore)
		self.widget.append_column(nameCol)
		self.widget.set_size_request(400, 300)

	def addItem(self, item):
		self.listStore.append([item])
		# TODO add to widget

	def addItems(self, items):
		for item in items:
			self.addItem(item)

	def compile(self):
		if not self.listStore.get_iter_root():
			return None
		playlist = Playlist()
		self.listStore.foreach(lambda model, path, iter, user_data: playlist.items.append(model.get_value(iter, 0).uri()), None)
		return playlist

class Control(object):
	def __init__(self, fifo, proc):
		self.file = fifo
		self.fifo = open(fifo, 'w')
		self.proc = proc

	def __del__(self):
		os.remove(self.file)
		self.fifo.close()

	def _expect(self, answer):
		self.fifo.flush()
		while True:
			if self.proc.poll() is not None:
				return None
			line = self.proc.stdout.readline().rstrip()
			command = line.split('=', 1)
			if command[0] != answer:
				continue
			return command[1]

	def seek(self, delta):
		self.fifo.write('seek {}\n'.format('+{}'.format(delta) if delta >= 0 else '{}'.format(delta)))

	def next(self):
		self.fifo.write('seek_chapter +1\n')

	def prev(self):
		self.fifo.write('seek_chapter -1\n')

	def getTime(self):
		self.fifo.write('get_time_pos\n')
		try:
			return self._expect('ANS_TIME_POSITION')
		except:
			return None

	def getTrack(self):
		pass

class Playlist(object):
	def __init__(self):
		self.items = []

	def play(self):
		try:
			os.mkfifo('/tmp/mplayer.fifo', 0660)
		except:
			pass
		proc = subprocess.Popen(['mplayer', '-playlist', '-', '-quiet', '-slave', '-input', 'file=/tmp/mplayer.fifo'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1)
		for i in self.items:
			proc.stdin.write(i)
			proc.stdin.write('\n')
		proc.stdin.close()
		return Control('/tmp/mplayer.fifo', proc)

def main():
	RootWindow()
	gtk.main()

if  __name__ == '__main__':
	main()
