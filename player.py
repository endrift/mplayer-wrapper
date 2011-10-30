#!/usr/bin/env python2
import pygtk
pygtk.require('2.0')
import gtk
import gobject

import os
import select
import signal
import subprocess

class RootWindow(object):
	def  __init__(self):
		self.icons = gtk.icon_theme_get_default()
		self.player = None

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect('delete_event', self.quit)
		self.window.set_title('Media Player')
		self.window.set_default_size(600, 300)
		hbox = gtk.HBox()
		self.window.add(hbox)
		controls = gtk.VBox()
		hbox.pack_start(controls, False, False, 0)
		extButton = gtk.Button('External Drive')
		extButton.connect('clicked', lambda w: self.selectFile('/'))
		ytButton = gtk.Button('YouTube Video')
		ytButton.connect('clicked', lambda w: self.selectYouTube())
		remoteButton = gtk.Button('Remote Filesystem')
		removeButton = gtk.Button('Remove Selected')
		controls.pack_start(extButton)
		controls.pack_start(ytButton)
		controls.pack_start(remoteButton)
		controls.pack_start(removeButton)

		player = gtk.VBox()
		hbox.pack_start(player)

		self.playlist = PlaylistWidget()
		player.pack_start(self.playlist.widget)

		self.scrubber = gtk.HScale()
		self.scrubber.set_draw_value(False)
		player.pack_end(self.scrubber, False, False, 0)

		playButton = gtk.Button();
		playButton.add(self._loadIcon('player_play'))
		playButton.connect('clicked', self.play)
		pauseButton = gtk.Button()
		pauseButton.add(self._loadIcon('player_pause'))
		pauseButton.connect('clicked', self.pause)
		stopButton = gtk.Button()
		stopButton.add(self._loadIcon('player_stop'))
		stopButton.connect('clicked', self.stop)
		controls.pack_start(playButton)
		controls.pack_start(pauseButton)
		controls.pack_start(stopButton)

		prevButton = gtk.Button()
		prevButton.add(self._loadIconSmall('player_rew'))
		prevButton.connect('clicked', self.prev)
		nextButton = gtk.Button()
		nextButton.add(self._loadIconSmall('player_fwd'))
		nextButton.connect('clicked', self.next)
		skipBox = gtk.HBox()
		skipBox.pack_start(prevButton)
		skipBox.pack_start(nextButton)
		controls.pack_start(skipBox)
		self.window.show_all()

	def _loadIcon(self, iconName):
		return gtk.image_new_from_pixbuf(self.icons.load_icon(iconName, 96, 0))

	def _loadIconSmall(self, iconName):
		return gtk.image_new_from_pixbuf(self.icons.load_icon(iconName, 48, 0))

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

	def update(self):
		if self.player:
			if self.player.ended():
				self.player = None
				return False

			try:
				self.scrubber.set_range(0, self.player.getDuration())
				self.scrubber.set_value(self.player.getTime())
			except:
				return not self.player.ended()

			return True
		return False

	def play(self, widget):
		if self.player and not self.player.ended():
			if self.player.paused():
				self.player.togglePause()
			return

		p = self.playlist.compile()
		if p:
			self.player = p.play()
			self.timer = gobject.timeout_add(500, self.update)
		else:
			error = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, None)
			error.set_markup('Cannot play empty playlist!')
			error.run()
			error.destroy()

	def pause(self, widget):
		if self.player:
			self.player.togglePause()

	def stop(self, widget):
		if self.player:
			self.player.quit()
			self.player = None
			pass

	def next(self, widget):
		if self.player:
			self.player.next()

	def prev(self, widget):
		if self.player:
			self.player.prev()

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

	def addItem(self, item):
		self.listStore.append([item])

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
		self.quit()

	def quit(self):
		try:
			self.proc.terminate()
			self.proc = None
		except:
			pass
		try:
			os.remove(self.file)
		except:
			pass

		self.fifo.close()

	def _write(self, command):
		if self.ended():
			return
		self.fifo.write(command)
		self.fifo.write('\n')
		self.fifo.flush()

	def _expect(self, answer, timeout=0):
		def onTimeout():
			raise RuntimeError('Timed out')

		self.fifo.flush()
		signal.signal(signal.SIGALRM, lambda no, fr: onTimeout())
		if timeout:
			signal.alarm(timeout)
		while True:
			if self.ended():
				signal.alarm(0)
				return None
			line = self.proc.stdout.readline().rstrip()
			command = line.split('=', 1)
			if command[0] != answer:
				continue
			signal.alarm(0)
			return command[1]

	def ended(self):
		return not self.proc or self.proc.poll() is not None

	def seek(self, delta):
		self._write('seek {}'.format('+{}'.format(delta) if delta >= 0 else '{}'.format(delta)))

	def next(self):
		self._write('pt_step +1')

	def prev(self):
		self._write('pt_step -1')

	def togglePause(self):
		self._write('pause')

	def getTime(self):
		self._write('pausing_keep_force get_time_pos')
		try:
			return float(self._expect('ANS_TIME_POSITION', 1))
		except:
			return None

	def getDuration(self):
		self._write('pausing_keep_force get_time_length')
		try:
			return float(self._expect('ANS_LENGTH', 1))
		except:
			return None

	def paused(self):
		self._write('pausing_keep_force get_property pause')
		try:
			return self._expect('ANS_pause', 1) == 'yes'
		except:
			return False

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
