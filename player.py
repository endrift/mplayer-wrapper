#!/usr/bin/env python
from gi.repository import Gtk, GObject
import os
import signal
import subprocess

class RootWindow(object):
	def  __init__(self):
		self.icons = Gtk.IconTheme.get_default()
		self.player = None

		self.window = Gtk.Window()
		self.window.connect('delete_event', self.quit)
		self.window.set_title('Media Player')
		self.window.set_default_size(600, 300)
		hbox = Gtk.HBox()
		self.window.add(hbox)
		controls = Gtk.VBox()
		hbox.pack_start(controls, False, False, 0)
		self.playlistControls = Gtk.VBox()
		controls.pack_start(self.playlistControls, True, True, 0)
		extButton = Gtk.Button('External Drive')
		extButton.connect('clicked', lambda w: self.selectFile('/'))
		ytButton = Gtk.Button('YouTube Video')
		ytButton.connect('clicked', lambda w: self.selectYouTube())
		remoteButton = Gtk.Button('Remote Filesystem')
		removeButton = Gtk.Button('Remove Selected')
		removeButton.connect('clicked', lambda w: self.removeSelected())
		self.playlistControls.pack_start(extButton, False, False, 0)
		self.playlistControls.pack_start(ytButton, False, False, 0)
		self.playlistControls.pack_start(removeButton, False, False, 0)

		player = Gtk.VBox()
		hbox.pack_start(player, True, True, 0)

		self.playlist = PlaylistWidget()
		scroller = Gtk.ScrolledWindow()
		scroller.add(self.playlist.widget)
		scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		player.pack_start(scroller, True, True, 0)

		self.scrubber = Gtk.HScale()
		self.scrubber.set_draw_value(False)
		self.scrubber.connect('adjust-bounds', lambda w, v: self.seek(v))
		player.pack_end(self.scrubber, False, False, 0)

		playButton = Gtk.Button();
		playButton.add(self._loadIcon('player_play'))
		playButton.connect('clicked', self.play)
		pauseButton = Gtk.Button()
		pauseButton.add(self._loadIcon('player_pause'))
		pauseButton.connect('clicked', self.pause)
		stopButton = Gtk.Button()
		stopButton.add(self._loadIcon('player_stop'))
		stopButton.connect('clicked', self.stop)
		controls.pack_start(playButton, False, False, 0)
		controls.pack_start(pauseButton, False, False, 0)
		controls.pack_start(stopButton, False, False, 0)

		prevButton = Gtk.Button()
		prevButton.add(self._loadIconSmall('player_rew'))
		prevButton.connect('clicked', self.prev)
		nextButton = Gtk.Button()
		nextButton.add(self._loadIconSmall('player_fwd'))
		nextButton.connect('clicked', self.next)
		skipBox = Gtk.HBox()
		skipBox.pack_start(prevButton, True, True, 0)
		skipBox.pack_start(nextButton, True, True, 0)
		controls.pack_start(skipBox, True, True, 0)
		self.window.show_all()

	def _loadIcon(self, iconName):
		return Gtk.Image.new_from_pixbuf(self.icons.load_icon(iconName, 96, 0))

	def _loadIconSmall(self, iconName):
		return Gtk.Image.new_from_pixbuf(self.icons.load_icon(iconName, 48, 0))

	def _setScrubberEnabled(self, enabled):
		self.scrubber.set_sensitive(enabled)
		if not enabled:
			self.scrubber.set_value(0)
		self._setPlaylistEnabled(not enabled)

	def _setPlaylistEnabled(self, enabled):
		self.playlist.widget.set_sensitive(enabled)
		self.playlistControls.set_sensitive(enabled)

	def removeSelected(self):
		self.playlist.removeSelected()

	def selectDrive(self):
		pass

	def selectFile(self, root):
		f = Gtk.FileChooserDialog('Select File', None, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		f.set_default_response(Gtk.ResponseType.CANCEL)
		f.set_select_multiple(True)
		f.set_current_folder(root)
		response = f.run()
		if response == Gtk.ResponseType.OK:
			self.playlist.addItems([LocalFile(name) for name in f.get_filenames()])
		f.destroy()

	def selectYouTube(self):
		ytWindow = Gtk.MessageDialog(None, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL, None)
		ytWindow.set_markup('Enter URL')
		ytWindow.connect('delete_event', lambda w,d: w.destroy())
		ytWindow.set_default_response(Gtk.ResponseType.CANCEL)
		inputBox = Gtk.Entry()
		ytWindow.vbox.pack_start(inputBox, False, False, 0)
		ytWindow.show_all()
		response = ytWindow.run()
		if response == Gtk.ResponseType.OK:
			try:
				self.playlist.addItem(YouTubeMovie(inputBox.get_text()))
			except:
				pass
		ytWindow.destroy()

	def update(self):
		if self.player:
			if self.player.ended():
				self._setScrubberEnabled(False)
				self.player = None
				return False

			try:
				self._setScrubberEnabled(True)
				self.scrubber.set_range(0, self.player.getDuration())
				self.scrubber.set_value(self.player.getTime())
			except:
				self._setScrubberEnabled(False)
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
			self._setScrubberEnabled(True)
			self.timer = GObject.timeout_add(500, self.update)
		else:
			error = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, None)
			error.set_markup('Cannot play empty playlist!')
			error.run()
			error.destroy()

	def pause(self, widget):
		if self.player:
			self.player.togglePause()

	def seek(self, value):
		if self.player:
			duration = self.player.getDuration()
			if not duration:
				self.stop()
				return
			if value > duration - 6:
				value = duration - 6
			self.player.seek(value)
			if value >= duration - 6:
				self.player.pause()

	def stop(self, widget=None):
		if self.player:
			self.player.quit()
			self._setScrubberEnabled(False)
			self.player = None
			pass

	def next(self, widget):
		if self.player:
			self.player.next()

	def prev(self, widget):
		if self.player:
			self.player.prev()

	def quit(self, widget, event, data=None):
		Gtk.main_quit()
		return False

class LocalFile(object):
	def __init__(self, filename):
		self.filename = filename

	def __repr__(self):
		return self.filename

	def uri(self):
		return self.filename

	def type(self):
		return 'File'

	def name(self):
		return self.filename

class YouTubeMovie(object):
	def __init__(self, url):
		if url.startswith('http://'):
			self.url = url
		else:
			self.url = 'http://www.youtube.com/watch?v={0}'.format(url)
		self.download = subprocess.check_output(['youtube-dl', '-g', self.url])
		self.title = subprocess.check_output(['youtube-dl', '-e', self.url]).rstrip()

	def __repr__(self):
		return 'YouTube: {0}'.format(self.url)

	def uri(self):
		return self.download

	def type(self):
		return 'YouTube'

	def name(self):
		return self.title

class PlaylistWidget(object):
	def __init__(self):
		def format_name(col, cell, model, iter, func_data):
			obj = model.get_value(iter, 0)
			cell.set_property('text', obj.name())

		def format_type(col, cell, model, iter, func_data):
			obj = model.get_value(iter, 0)
			cell.set_property('text', obj.type())

		self.listStore = Gtk.ListStore(object)
		nameText = Gtk.CellRendererText()
		nameCol = Gtk.TreeViewColumn('Name', nameText)
		nameCol.set_cell_data_func(nameText, format_name)
		typeText = Gtk.CellRendererText()
		typeCol = Gtk.TreeViewColumn('Type', typeText)
		typeCol.set_cell_data_func(typeText, format_type)
		self.widget = Gtk.TreeView()
		self.widget.set_model(self.listStore)
		self.widget.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
		self.widget.set_reorderable(True)
		self.widget.append_column(nameCol)
		self.widget.append_column(typeCol)

	def addItem(self, item):
		self.listStore.append([item])

	def addItems(self, items):
		for item in items:
			self.addItem(item)

	def removeSelected(self):
		selected = self.widget.get_selection()
		model, rows = selected.get_selected_rows()
		iters = [model.get_iter(row) for row in rows]
		for i in iters:
			model.remove(i)

	def compile(self):
		if not self.listStore.get_iter_first():
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
		self._write('seek {0}'.format('+{0}'.format(delta) if delta >= 0 else '{0}'.format(delta)))

	def next(self):
		self._write('pt_step +1')

	def prev(self):
		self._write('pt_step -1')

	def togglePause(self):
		self._write('pause')

	def pause(self):
		if not self.paused():
			self.togglePause()

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

	def seek(self, value):
		self._write('seek {0} 2'.format(value))

	def getTrack(self):
		pass

class Playlist(object):
	def __init__(self):
		self.items = []

	def play(self):
		try:
			os.mkfifo('/tmp/mplayer.fifo', 0o0660)
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
	Gtk.main()

if  __name__ == '__main__':
	main()
