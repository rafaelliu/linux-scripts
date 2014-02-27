#!/usr/bin/python
# default in python 3+
from __future__ import division

import sys

import operator
import logging

import xpybutil                                       
import xpybutil.event as event
import xpybutil.window as window
import xpybutil.util as util                                                                                          
import xpybutil.xinerama as xinerama
import xpybutil.rect as rect
import xpybutil.ewmh as ewmh
from xpybutil.ewmh import State

logging.basicConfig(level=logging.DEBUG)

class Adjacency(object):
	NONE = 0
	tt = 1
	tb = 2
	bt = 3
	bb = 4
	ll = 5
	rl = 6
	lr = 7
	rr = 8

class Rectangle(object):
	
	def __init__(self, x, y, width, height):
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		
	def get_adjacency(self, other):
		this_left = self.x
		this_right = self.x + self.width
		this_top = self.y
		this_bottom = self.y + self.height

		other_left = other.x
		other_right = other.x + other.width
		other_top = other.y
		other_bottom = other.y + other.height
		
		adjacencies = []
		if (this_top == other_top):
			adjacencies.append(Adjacency.tt)

		if (this_top == other_bottom):
			adjacencies.append(Adjacency.tb)

		if (this_bottom == other_top):
			adjacencies.append(Adjacency.bt)

		if (this_bottom == other_bottom):
			adjacencies.append(Adjacency.bb)

		if (this_left == other_left):
			adjacencies.append(Adjacency.ll)

		if (this_left == other_right):
			adjacencies.append(Adjacency.lr)

		if (this_right == other_left):
			adjacencies.append(Adjacency.rl)

		if (this_right == other_right):
			adjacencies.append(Adjacency.rr)
							 
		return adjacencies

	def get_area(self):
		return (self.width * self.height)

	# x.get_intersection(y) == y.get_intersection(x)
	def get_intersection(self, other):
		# get final coords
		x = max(self.x, other.x)
		y = max(self.y, other.y)
		width = min(self.x + self.width, other.x + other.width) - x
		height = min(self.y + self.height, other.y + other.height) - y
		
		if width < 0 or height < 0:
			return None

		return Rectangle(x, y, width, height)

	def to_tuple(self):
		return (self.x, self.y, self.width, self.height)
	
	def __str__( self ):
			return "<Rect (x=%s,y=%s,width=%s,height=%s)>" % (self.x,self.y, self.width,self.height)

class TileManager(object):
	
	"""
	How much of the window's width got to be in the monitor for
	TileManager to consider that is the monitor the window is in
	"""
	__THRESHOLD = 0.6
	
	def __init__(self):
		self.window_manager = self.get_window_manager()
		monitors = xinerama.get_monitors()
		self.workareas = [ Rectangle(*mon) for mon in rect.monitor_rects(monitors) ]
		self.workareas = sorted(self.workareas, key=lambda rect: rect.x) 
	
	def get_tile(self, wid):
		return Tile(wid, self.window_manager)
	
	def get_window_manager(self):
		utilwm = window.WindowManagers.Unknown
		w = ewmh.get_supporting_wm_check(xpybutil.root).reply()
		if w:
			childw = ewmh.get_supporting_wm_check(w).reply()
			if childw == w:
				wm = ewmh.get_wm_name(childw).reply()
				if wm.lower() == 'openbox':
						utilwm = window.WindowManagers.Openbox
				elif wm.lower() == 'kwin':
						utilwm = window.WindowManagers.KWin

				logging.info( '%s window manager is running...' % wm )
		
		return utilwm

	def get_monitor_idx(self, wid):
		win_rect = self.get_tile(wid).get_geometry()
		win_area = win_rect.get_area()
		logging.debug("Window area is: %s" % win_rect)

		# if any attend to threshold, return it
		areas = {}
		for idx, mon_geom in enumerate(self.workareas):
			intersec = win_rect.get_intersection(mon_geom)
			logging.debug( "Interseciont with monitor %d is: %s" % (idx, intersec) )
			if intersec == None:
				areas[idx] = 0
				continue
				
			areas[idx] = intersec.get_area()
			if (areas[idx] / win_area >= self.__THRESHOLD):
				logging.debug( "Threashold met for monitor %d" % idx )
				return idx
		
		# if not, return the greater
		max_tuple = max(areas.iteritems(), key=operator.itemgetter(1))
		return max_tuple[0]
		
	def get_monitor_areas(self):
		return self.workareas

	def get_monitor_area(self, mid):
		return self.workareas[mid]

	def get_active_window(self):
		return ewmh.get_active_window().reply()

class Tile(object):

	def __init__(self, wid, window_manager):
		self.wid = wid
		self.window_manager = window_manager

	def is_maximized(self):
		vatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_VERT')
		hatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_HORZ')
		
		states = ewmh.get_wm_state(self.wid).reply()
		
		return vatom in states and hatom in states
		
	def maximize(self):
		vatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_VERT')
		hatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_HORZ')
		ewmh.request_wm_state_checked(self.wid, State.Add, vatom, hatom).check()

	def unmaximize(self):
		vatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_VERT')
		hatom = util.get_atom('_NET_WM_STATE_MAXIMIZED_HORZ')
		ewmh.request_wm_state_checked(self.wid, State.Remove, vatom, hatom).check()

	# nao funfa!!
	def minimize(self):
		atom = util.get_atom('_NET_WM_STATE_HIDDEN')
		ewmh.request_wm_state_checked(self.wid, State.Add, atom).check()

	def activate(self):
		ewmh.request_active_window_checked(self.wid, source=1).check()

	def moveresize(self, x=None, y=None, w=None, h=None):
		self.unmaximize()
		window.moveresize(self.wid, x, y, w, h, self.window_manager)
		
	def get_geometry(self):
		return Rectangle(*window.get_geometry(wid, self.window_manager))


#def cb_property_notify(e):                                                                                            
#     aname = util.get_atom_name(e.atom)                                                                                
#     print aname                                                                                                       
#     print e                                                                                                           
#                                                                                                                       
#window.listen(xpybutil.root, 'PropertyChange')                                                                        
#event.connect('PropertyNotify', xpybutil.root, cb_property_notify)                                                    
#event.main()

action = sys.argv[1]

# do stuff
tm = TileManager()
wid = tm.get_active_window()
mid = tm.get_monitor_idx(wid)
tile = tm.get_tile(wid)

logging.debug(tm.get_monitor_areas())

for area in tm.get_monitor_areas():
	logging.debug("%s", area)

if action in ["left", "right", "top", "bottom"]:

	win_rect = tile.get_geometry()
	mon_rect = tm.get_monitor_area(mid)
	print mon_rect

	if action == "left":
		
		logging.debug("Tiling left")

		if Adjacency.ll in win_rect.get_adjacency(mon_rect):
			logging.debug("Window is adjacent to the left of %d" % mid )
			if mid - 1 >= 0:
				mid = mid - 1
				mon_rect = tm.get_monitor_area(mid)

				mon_rect.x = mon_rect.x + mon_rect.width/2
				mon_rect.width = mon_rect.width/2
				logging.debug("There's a monitor do the left, moving to %d (%s)" % ( mid, mon_rect ) )
		else:
			logging.debug("There's a monitor do the left, moving to %d (%s)" % ( mid, mon_rect ) )
			mon_rect.width = mon_rect.width/2

	elif action == "right":
		
		logging.debug("Tiling right")

		if Adjacency.rr in win_rect.get_adjacency(mon_rect):
			logging.debug("Window is adjacent to the right of %d" % mid )
			if mid + 1 < len(tm.get_monitor_areas()):
				mid = mid + 1
				mon_rect = tm.get_monitor_area(mid)

				mon_rect.width = mon_rect.width/2
				logging.debug("There's a monitor do the right, moving to %d (%s)" % ( mid, mon_rect ) )
		else:
			mon_rect.x = mon_rect.x + mon_rect.width/2
			mon_rect.width = mon_rect.width/2

	if action == "top":
		mon_rect.height = mon_rect.height/2
	elif action == "bottom":
		mon_rect.y = mon_rect.y + mon_rect.height/2
		mon_rect.height = mon_rect.height/2

	tile.moveresize(*mon_rect.to_tuple())

else:
	
	if action == "min":
		tile.minimize()
	elif action == "max":
		if tile.is_maximized():
			tile.unmaximize()
		else:
			tile.maximize()
	else:
		logging.error("Invalid parameter")

xpybutil.conn.flush()
