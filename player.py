#!/usr/bin/env python2
import pygtk
pygtk.require('2.0')
import gtk

import os
import select
import subprocess

class RootWindow(object):
	def  __init__(self):
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect('delete_event', self.quit)
		self.window.set_title('Media Player')
		vbox = gtk.VBox(False, 0)
		self.window.add(vbox)
		topLabel = gtk.Label('Please select a media source')
		vbox.pack_start(topLabel)
		self.window.show_all()

	def quit(self, widget, event, data=None):
		gtk.main_quit()
		return False

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
		proc.stdin.close()
		return Control('/tmp/mplayer.fifo', proc)

def main():
	RootWindow()
	gtk.main()

if  __name__ == '__main__':
	main()
