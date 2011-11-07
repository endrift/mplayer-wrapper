#!/usr/bin/env python2
import pygtk
pygtk.require('2.0')
import gtk
import gobject

import fcntl
import functools
import os
import select
import signal
import subprocess

class RootWindow(object):
	icons = gtk.icon_theme_get_default()
	def  __init__(self):
		self.player = None

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect('delete_event', self.quit)
		self.window.set_title('Media Player')
		self.window.set_default_size(600, 300)
		hbox = gtk.HBox()
		self.window.add(hbox)
		controls = gtk.VBox()
		hbox.pack_start(controls, False, False, 0)
		self.playlistControls = gtk.VBox()
		controls.pack_start(self.playlistControls, True, True, 0)
		extButton = gtk.Button('External Drive')
		extButton.connect('clicked', lambda w: self.selectFile('/'))
		folderButton = gtk.Button('Folder')
		folderButton.connect('clicked', lambda w: self.selectFolder('/'))
		ytButton = gtk.Button('YouTube Video')
		ytButton.connect('clicked', lambda w: self.selectYouTube())
		removeButton = gtk.Button('Remove Selected')
		removeButton.connect('clicked', lambda w: self.removeSelected())
		removeAllButton = gtk.Button('Remove All')
		removeAllButton.connect('clicked', lambda w: self.removeAll())
		self.playlistControls.pack_start(extButton)
		self.playlistControls.pack_start(folderButton)
		self.playlistControls.pack_start(ytButton)
		self.playlistControls.pack_start(removeButton)
		self.playlistControls.pack_start(removeAllButton)

		player = gtk.VBox()
		hbox.pack_start(player)

		self.playlist = PlaylistWidget()
		scroller = gtk.ScrolledWindow()
		scroller.add(self.playlist.widget)
		scroller.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		player.pack_start(scroller)

		self.scrubber = gtk.HScale()
		self.scrubber.set_draw_value(False)
		self.scrubber.connect('adjust-bounds', lambda w, v: self.seek(v))
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
		prevButton.add(self._loadIconSmall('player_start'))
		prevButton.connect('clicked', self.prev)
		nextButton = gtk.Button()
		nextButton.add(self._loadIconSmall('player_end'))
		nextButton.connect('clicked', self.next)
		skipBox = gtk.HBox()
		skipBox.pack_start(prevButton)
		skipBox.pack_start(nextButton)
		controls.pack_start(skipBox)

		seekBox = gtk.HBox()
		seekBackButton = gtk.Button()
		seekBackButton.add(self._loadIconSmall('player_rew'))
		seekBackButton.connect('clicked', lambda w: self.seekDelta(-10))
		seekBox.pack_start(seekBackButton)
		seekForwardButton = gtk.Button()
		seekForwardButton.add(self._loadIconSmall('player_fwd'))
		seekForwardButton.connect('clicked', lambda w: self.seekDelta(10))
		seekBox.pack_start(seekForwardButton)
		controls.pack_start(seekBox)

		dvdbox = gtk.Table(3, 3, True)
		upButton = gtk.Button()
		upButton.add(self._loadIconTiny('go-up'))
		upButton.connect('clicked', lambda w: self.dvdControl('up'))
		dvdbox.attach(upButton, 1, 2, 0, 1)
		leftButton = gtk.Button()
		leftButton.add(self._loadIconTiny('go-previous'))
		leftButton.connect('clicked', lambda w: self.dvdControl('left'))
		dvdbox.attach(leftButton, 0, 1, 1, 2)
		downButton = gtk.Button()
		downButton.add(self._loadIconTiny('go-down'))
		downButton.connect('clicked', lambda w: self.dvdControl('down'))
		dvdbox.attach(downButton, 1, 2, 2, 3)
		rightButton = gtk.Button()
		rightButton.add(self._loadIconTiny('go-next'))
		rightButton.connect('clicked', lambda w: self.dvdControl('right'))
		dvdbox.attach(rightButton, 2, 3, 1, 2)

		selectButton = gtk.Button('OK')
		selectButton.connect('clicked', lambda w: self.dvdControl('select'))
		dvdbox.attach(selectButton, 1, 2, 1, 2)

		lastChapterButton = gtk.Button()
		lastChapterButton.add(self._loadIconTiny('go-first'))
		lastChapterButton.connect('clicked', lambda w: self.seekChapter(-1))
		dvdbox.attach(lastChapterButton, 0, 1, 0, 1)
		nextChapterButton = gtk.Button()
		nextChapterButton.add(self._loadIconTiny('go-last'))
		nextChapterButton.connect('clicked', lambda w: self.seekChapter(1))
		dvdbox.attach(nextChapterButton, 2, 3, 0, 1)

		menuButton = gtk.Button()
		menuButton.add(self._loadIconTiny('undo'))
		menuButton.connect('clicked', lambda w: self.dvdControl('menu'))
		dvdbox.attach(menuButton, 0, 1, 2, 3)
		ejectButton = gtk.Button()
		ejectButton.add(self._loadIconTiny('player_eject'))
		ejectButton.connect('clicked', lambda w: self.eject())
		dvdbox.attach(ejectButton, 2, 3, 2, 3)

		controls.pack_start(dvdbox)

		languageBox = gtk.HBox()
		subsButton = gtk.Button('Subs')
		subsButton.connect('clicked', lambda w: self.cycleSubs())
		languageBox.pack_start(subsButton)
		langButton = gtk.Button('Lang')
		langButton.connect('clicked', lambda w: self.cycleLanguage())
		languageBox.pack_start(langButton)
		controls.pack_start(languageBox)

		self.window.show_all()

	@staticmethod
	def _loadIcon(iconName):
		return gtk.image_new_from_pixbuf(RootWindow.icons.load_icon(iconName, 96, 0))

	@staticmethod
	def _loadIconSmall(iconName):
		return gtk.image_new_from_pixbuf(RootWindow.icons.load_icon(iconName, 48, 0))

	@staticmethod
	def _loadIconTiny(iconName):
		return gtk.image_new_from_pixbuf(RootWindow.icons.load_icon(iconName, 32, 0))

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

	def removeAll(self):
		self.playlist.clear()

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

	def selectFolder(self, root):
		f = gtk.FileChooserDialog('Select Folder', None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		f.set_default_response(gtk.RESPONSE_CANCEL)
		f.set_select_multiple(True)
		f.set_create_folders(False)
		f.set_current_folder(root)
		response = f.run()
		if response == gtk.RESPONSE_OK:
			paths = functools.reduce(list.__add__, [os.walk(name) for name in f.get_filenames()])
			files = functools.reduce(list.__add__, [[os.path.join(root, file) for file in files] for root, dirs, files in paths])
			files.sort()
			self.playlist.addItems([LocalFile(name) for name in files])
		f.destroy()

	def selectYouTube(self):
		ytWindow = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, None)
		ytWindow.set_markup('Enter URL')
		ytWindow.connect('delete_event', lambda w,d: w.destroy())
		ytWindow.set_default_response(gtk.RESPONSE_OK)
		inputBox = gtk.Entry()
		ytWindow.vbox.pack_start(inputBox)
		ytWindow.show_all()
		response = ytWindow.run()
		if response == gtk.RESPONSE_OK and inputBox.get_text():
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
			self.timer = gobject.timeout_add(500, self.update)
		else:
			error = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, None)
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

	def next(self, widget):
		if self.player:
			self.player.next()

	def prev(self, widget):
		if self.player:
			self.player.prev()

	def seekDelta(self, delta):
		if self.player:
			self.player.seekDelta(delta)

	def cycleSubs(self):
		if self.player:
			self.player.cycleSubs()

	def cycleLanguage(self):
		if self.player:
			self.player.cycleLanguage()

	def dvdControl(self, control):
		if self.player:
			self.player.dvdControl(control)

	def seekChapter(self, direction):
		if self.player:
			self.player.seekChapter(direction)

	def eject(self):
		try:
			cd = os.open('/dev/sr0', os.O_RDONLY)
			fcntl.ioctl(cd, 0x5309)
			os.close(cd)
		except:
			print('Could not eject CD')

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

	@staticmethod
	def type():
		return 'File'

	def name(self):
		return self.filename

class YouTubeMovie(object):
	def __init__(self, url):
		if url.startswith('http://'):
			self.url = url
		else:
			self.url = 'http://www.youtube.com/watch?v={0}'.format(url)
		self.download = self._pollProc(['-g'])
		self.title = self._pollProc(['-e']).rstrip()

	def _pollProc(self, type):
		command = ['youtube-dl']
		command.extend(type)
		command.append(self.url)
		proc = subprocess.Popen(command, stdout=subprocess.PIPE)
		(out, err) = proc.communicate()
		if proc.returncode:
			raise subprocess.CalledProcessError(proc.returncode, ' '.join(command))
		return out

	def __repr__(self):
		return 'YouTube: {0}'.format(self.url)

	def uri(self):
		return self.download

	@staticmethod
	def type():
		return 'YouTube'

	def name(self):
		return self.title

class PlaylistWidget(object):
	def __init__(self):
		def format_name(col, cell, model, iter):
			obj = model.get_value(iter, 0)
			cell.set_property('text', obj.name())

		def format_type(col, cell, model, iter):
			obj = model.get_value(iter, 0)
			cell.set_property('text', obj.type())

		self.listStore = gtk.ListStore(object)
		nameText = gtk.CellRendererText()
		nameCol = gtk.TreeViewColumn('Name', nameText)
		nameCol.set_cell_data_func(nameText, format_name)
		typeText = gtk.CellRendererText()
		typeCol = gtk.TreeViewColumn('Type', typeText)
		typeCol.set_cell_data_func(typeText, format_type)
		self.widget = gtk.TreeView(self.listStore)
		self.widget.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
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

	def clear(self):
		self.listStore.clear()

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

	def seekDelta(self, delta):
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

	def seekChapter(self, direction):
		self._write('seek_chapter {0}'.format(direction))

	def getTrack(self):
		pass

	def cycleSubs(self):
		self._write('sub_select')

	def cycleLanguage(self):
		self._write('switch_audio')
		
	def dvdControl(self, control):
		self._write('dvdnav {0}'.format(control))

class Playlist(object):
	def __init__(self):
		self.items = []

	def play(self):
		try:
			os.remove('/tmp/mplayer.fifo')
		except:
			pass
		try:
			os.mkfifo('/tmp/mplayer.fifo', 0o660)
		except:
			pass
		proc = subprocess.Popen(['mplayer', '-playlist', '-', '-quiet', '-slave', '-input', 'file=/tmp/mplayer.fifo'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1)
		for i in self.items:
			proc.stdin.write(i)
			proc.stdin.write('\n')
		proc.stdin.close()
		return Control('/tmp/mplayer.fifo', proc)

def main():
	try:
		RootWindow()
		gtk.main()
	finally:
		try:
			os.remove('/tmp/mplayer.fifo')
		except:
			pass

if  __name__ == '__main__':
	main()
