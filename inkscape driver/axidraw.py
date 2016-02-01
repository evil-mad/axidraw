# axidraw.py
# Part of the AxiDraw driver for Inkscape
# https://github.com/evil-mad/AxiDraw
#
# Version 1.0.0, dated January 31, 2016.
# 
# Requires Pyserial 2.7.0 or newer. Pyserial 3.0 recommended.
#
# Copyright 2016 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


from simpletransform import *
import gettext
import simplepath
import serial
import string
import time

import plot_utils		# https://github.com/evil-mad/plotink
import ebb_serial		# https://github.com/evil-mad/plotink
import ebb_motion		# https://github.com/evil-mad/plotink  Requires version 0.4

import axidraw_conf       	#Some settings can be changed here.

F_DEFAULT_SPEED = 1
N_PEN_DOWN_DELAY = 400    # delay (ms) for the pen to go down before the next move
N_PEN_UP_DELAY = 400      # delay (ms) for the pen to up down before the next move

N_PEN_UP_POS = 50      # Default pen-up position
N_PEN_DOWN_POS = 40      # Default pen-down position

N_SERVOSPEED = 50			# Default pen-lift speed 
N_DEFAULT_LAYER = 1			# Default inkscape layer

class WCB( inkex.Effect ):

	def __init__( self ):
		inkex.Effect.__init__( self )
		self.OptionParser.add_option( "--tab",
			action="store", type="string",
			dest="tab", default="controls",
			help="The active tab when Apply was pressed" )
			
		self.OptionParser.add_option( "--penUpPosition",
			action="store", type="int",
			dest="penUpPosition", default=N_PEN_UP_POS,
			help="Position of pen when lifted" )
		self.OptionParser.add_option( "--penDownPosition",
			action="store", type="int",
			dest="penDownPosition", default=N_PEN_DOWN_POS,
			help="Position of pen for painting" )	
			 
		self.OptionParser.add_option( "--setupType",
			action="store", type="string",
			dest="setupType", default="controls",
			help="The active option when Apply was pressed" )
			
		self.OptionParser.add_option( "--penDownSpeed",
			action="store", type="int",
			dest="penDownSpeed", default=F_DEFAULT_SPEED,
			help="Speed (step/sec) while pen is down." )
		self.OptionParser.add_option( "--penUpSpeed",
			action="store", type="int",
			dest="penUpSpeed", default=F_DEFAULT_SPEED,
			help="Speed (step/sec) while pen is up." )
		self.OptionParser.add_option( "--rapidSpeed",
			action="store", type="int",
			dest="rapidSpeed", default=F_DEFAULT_SPEED,
			help="Rapid speed (percent) while pen is up." )


		self.OptionParser.add_option( "--ServoUpSpeed",
			action="store", type="int",
			dest="ServoUpSpeed", default=N_SERVOSPEED,
			help="Rate of lifting pen " )
		self.OptionParser.add_option( "--penUpDelay",
			action="store", type="int",
			dest="penUpDelay", default=N_PEN_UP_DELAY,
			help="Delay after pen up (msec)." )
		self.OptionParser.add_option( "--ServoDownSpeed",
			action="store", type="int",
			dest="ServoDownSpeed", default=N_SERVOSPEED,
			help="Rate of lowering pen " ) 
		self.OptionParser.add_option( "--penDownDelay",
			action="store", type="int",
			dest="penDownDelay", default=N_PEN_DOWN_DELAY,
			help="Delay after pen down (msec)." )
			
		self.OptionParser.add_option( "--revMotor1",
			action="store", type="inkbool",
			dest="revMotor1", default=False,
			help="Reverse motion of X motor." )
		self.OptionParser.add_option( "--revMotor2",
			action="store", type="inkbool",
			dest="revMotor2", default=False,
			help="Reverse motion of Y motor." )
			
		self.OptionParser.add_option( "--smoothness",
			action="store", type="float",
			dest="smoothness", default=.2,
			help="Smoothness of curves" )

		self.OptionParser.add_option( "--resolution",
			action="store", type="int",
			dest="resolution", default=3,
			help="Resolution factor." )	

		self.OptionParser.add_option( "--manualType",
			action="store", type="string",
			dest="manualType", default="controls",
			help="The active option when Apply was pressed" )
		self.OptionParser.add_option( "--WalkDistance",
			action="store", type="float",
			dest="WalkDistance", default=1,
			help="Distance for manual walk" )			
			
		self.OptionParser.add_option( "--resumeType",
			action="store", type="string",
			dest="resumeType", default="controls",
			help="The active option when Apply was pressed" )			
			
		self.OptionParser.add_option( "--layernumber",
			action="store", type="int",
			dest="layernumber", default=N_DEFAULT_LAYER,
			help="Selected layer for multilayer plotting" )			

		self.serialPort = None
		self.bPenIsUp = None  #Initial state of pen is neither up nor down, but _unknown_.
		self.virtualPenIsUp = False  #Keeps track of pen postion when stepping through plot before resuming
		self.ignoreLimits = False

		self.fX = None
		self.fY = None 
		self.fCurrX = axidraw_conf.F_StartPos_X
		self.fCurrY = axidraw_conf.F_StartPos_Y 
		self.ptFirst = ( axidraw_conf.F_StartPos_X, axidraw_conf.F_StartPos_Y)
		self.bStopped = False
		self.fSpeed = 1
		self.resumeMode = False
		self.nodeCount = int( 0 )		#NOTE: python uses 32-bit ints.
		self.nodeTarget = int( 0 )
		self.pathcount = int( 0 )
		self.LayersFoundToPlot = False
		
		#Values read from file:
		self.svgLayer_Old = int( 0 )
		self.svgNodeCount_Old = int( 0 )
		self.svgDataRead_Old = False
		self.svgLastPath_Old = int( 0 )
		self.svgLastPathNC_Old = int( 0 )
		self.svgLastKnownPosX_Old = float( 0.0 )
		self.svgLastKnownPosY_Old = float( 0.0 )
		self.svgPausedPosX_Old = float( 0.0 )
		self.svgPausedPosY_Old = float( 0.0 )	
		
		#New values to write to file:
		self.svgLayer = int( 0 )
		self.svgNodeCount = int( 0 )
		self.svgDataRead = False
		self.svgLastPath = int( 0 )
		self.svgLastPathNC = int( 0 )
		self.svgLastKnownPosX = float( 0.0 )
		self.svgLastKnownPosY = float( 0.0 )
		self.svgPausedPosX = float( 0.0 )
		self.svgPausedPosY = float( 0.0 )	

		self.backlashStepsX = int(0)
		self.backlashStepsY = int(0)	 
		self.XBacklashFlag = True
		self.YBacklashFlag = True
		
		self.paintdist = 0.0
		self.manConfMode = False
		self.PrintFromLayersTab = False
		self.xErr = 0.0
		self.yErr = 0.0

		self.svgWidth = 0 
		self.svgHeight = 0
		
		self.xBoundsMax = axidraw_conf.N_PAGE_WIDTH
		self.xBoundsMin = axidraw_conf.F_StartPos_X
		self.yBoundsMax = axidraw_conf.N_PAGE_HEIGHT
		self.yBoundsMin = axidraw_conf.F_StartPos_Y		
		
		self.svgTransform = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
		
		self.stepsPerInch = 0 # must be set to a nonzero value before plotting.
		self.BrushUpSpeed   = float(10 * axidraw_conf.F_Speed_Scale) #speed when brush is up
		self.BrushDownSpeed = float(10 * axidraw_conf.F_Speed_Scale) #speed when brush is down		
					
		# So that we only generate a warning once for each
		# unsupported SVG element, we use a dictionary to track
		# which elements have received a warning
		self.warnings = {}
			
		self.preResumeMove = False
 
	def effect( self ):
		'''Main entry point: check to see which tab is selected, and act accordingly.'''

		self.svg = self.document.getroot()
		self.CheckSVGforWCBData()
		useOldResumeData = True

		skipSerial = False
		if (self.options.tab == '"Help"'):
			skipSerial = True
 		if (self.options.tab == '"options"'):
			skipSerial = True 		
 		if (self.options.tab == '"timing"'):
			skipSerial = True
 		
 		if skipSerial == False:
 			self.serialPort = ebb_serial.openPort()
 			if self.serialPort is None:
				inkex.errormsg( gettext.gettext( "Failed to connect to AxiDraw. :(" ) )
		
			if self.options.tab == '"splash"': 
				self.LayersFoundToPlot = False
				useOldResumeData = False
				self.PrintFromLayersTab = False
				self.plotCurrentLayer = True
				if self.serialPort is not None:
					self.svgNodeCount = 0
					self.svgLastPath = 0
					unused_button = ebb_motion.QueryPRGButton(self.serialPort)	#Query if button pressed
					self.svgLayer = 12345;  # indicate (to resume routine) that we are plotting all layers.
					self.plotToWCB()

			elif self.options.tab == '"resume"':
				if self.serialPort is None:
					useOldResumeData = True
				else:
					useOldResumeData = False
					unused_button = ebb_motion.QueryPRGButton(self.serialPort)	#Query if button pressed
					self.resumePlotSetup()
					if self.resumeMode:
						self.fX = self.svgPausedPosX_Old + axidraw_conf.F_StartPos_X
						self.fY = self.svgPausedPosY_Old + axidraw_conf.F_StartPos_Y
		 				self.resumeMode = False
		 				
		 				self.preResumeMove = True
						self.plotLineAndTime(self.fX, self.fY) #Special pre-resume move
						self.preResumeMove = False
						self.resumeMode = True
						self.nodeCount = 0
						self.plotToWCB() 
						
					elif ( self.options.resumeType == "justGoHome" ):
						self.fX = axidraw_conf.F_StartPos_X
						self.fY = axidraw_conf.F_StartPos_Y 
						self.plotLineAndTime(self.fX, self.fY)
		
						#New values to write to file:
						self.svgNodeCount = self.svgNodeCount_Old
						self.svgLastPath = self.svgLastPath_Old 
						self.svgLastPathNC = self.svgLastPathNC_Old 
						self.svgPausedPosX = self.svgPausedPosX_Old 
						self.svgPausedPosY = self.svgPausedPosY_Old
						self.svgLayer = self.svgLayer_Old 
		
					else:
						inkex.errormsg( gettext.gettext( "There does not seem to be any in-progress plot to resume." ) )
	
			elif self.options.tab == '"layers"':
				useOldResumeData = False 
				self.PrintFromLayersTab = True
				self.plotCurrentLayer = False
				self.LayersFoundToPlot = False
				self.svgLastPath = 0
				if self.serialPort is not None:
					unused_button = ebb_motion.QueryPRGButton(self.serialPort)	#Query if button pressed
					self.svgNodeCount = 0;
					self.svgLayer = self.options.layernumber
					self.plotToWCB()

			elif self.options.tab == '"setup"':
				self.setupCommand()
				
			elif self.options.tab == '"manual"':
				if self.options.manualType == "strip-data":
					for node in self.svg.xpath( '//svg:WCB', namespaces=inkex.NSS ):
						self.svg.remove( node )
					for node in self.svg.xpath( '//svg:eggbot', namespaces=inkex.NSS ):
						self.svg.remove( node )
					inkex.errormsg( gettext.gettext( "I've removed all AxiDraw data from this SVG file. Have a great day!" ) )
					return	
				else:	
					useOldResumeData = False 
					self.svgNodeCount = self.svgNodeCount_Old
					self.svgLastPath = self.svgLastPath_Old 
					self.svgLastPathNC = self.svgLastPathNC_Old 
					self.svgPausedPosX = self.svgPausedPosX_Old 
					self.svgPausedPosY = self.svgPausedPosY_Old
					self.svgLayer = self.svgLayer_Old 
					self.manualCommand()

		if (useOldResumeData):	#Do not make any changes to data saved from SVG file.
			self.svgNodeCount = self.svgNodeCount_Old
			self.svgLastPath = self.svgLastPath_Old 
			self.svgLastPathNC = self.svgLastPathNC_Old 
			self.svgPausedPosX = self.svgPausedPosX_Old 
			self.svgPausedPosY = self.svgPausedPosY_Old
			self.svgLayer = self.svgLayer_Old 				
			self.svgLastKnownPosX = self.svgLastKnownPosX_Old
			self.svgLastKnownPosY = self.svgLastKnownPosY_Old 

		self.svgDataRead = False
		self.UpdateSVGWCBData( self.svg )
		if self.serialPort is not None:
			ebb_motion.doTimedPause(self.serialPort, 10) #Pause a moment for underway commands to finish...
			ebb_serial.closePort(self.serialPort)	
		
	def resumePlotSetup( self ):
		self.LayerFound = False
		if ( self.svgLayer_Old < 101 ) and ( self.svgLayer_Old >= 0 ):
			self.options.layernumber = self.svgLayer_Old 
			self.PrintFromLayersTab = True
			self.plotCurrentLayer = False
			self.LayerFound = True
		elif ( self.svgLayer_Old == 12345 ):  # Plot all layers 
			self.PrintFromLayersTab = False
			self.plotCurrentLayer = True
			self.LayerFound = True 	
		if ( self.LayerFound ):
			if ( self.svgNodeCount_Old > 0 ):
				self.nodeTarget = self.svgNodeCount_Old
				self.svgLayer = self.svgLayer_Old
				if self.options.resumeType == "ResumeNow":
					self.resumeMode = True
				if self.serialPort is None:
					return
				self.ServoSetup()
				self.penUp() 
				self.EnableMotors() #Set plotting resolution  
				self.fSpeed = self.options.penUpSpeed
				self.fCurrX = self.svgLastKnownPosX_Old + axidraw_conf.F_StartPos_X
				self.fCurrY = self.svgLastKnownPosY_Old + axidraw_conf.F_StartPos_Y
				 

	def CheckSVGforWCBData( self ):
		self.svgDataRead = False
		self.recursiveWCBDataScan( self.svg )
		if ( not self.svgDataRead ):    #if there is no WCB data, add some:
			WCBlayer = inkex.etree.SubElement( self.svg, 'WCB' )
			WCBlayer.set( 'layer', str( 0 ) )
			WCBlayer.set( 'node', str( 0 ) )			#node paused at, if saved in paused state
			WCBlayer.set( 'lastpath', str( 0 ) )		#Last path number that has been fully painted
			WCBlayer.set( 'lastpathnc', str( 0 ) )		#Node count as of finishing last path.
			WCBlayer.set( 'lastknownposx', str( 0 ) )  #Last known position of carriage
			WCBlayer.set( 'lastknownposy', str( 0 ) )
			WCBlayer.set( 'pausedposx', str( 0 ) )	   #The position of the carriage when "pause" was pressed.
			WCBlayer.set( 'pausedposy', str( 0 ) )
						
	def recursiveWCBDataScan( self, aNodeList ):
		if ( not self.svgDataRead ):
			for node in aNodeList:
				if node.tag == 'svg':
					self.recursiveWCBDataScan( node )
				elif node.tag == inkex.addNS( 'WCB', 'svg' ) or node.tag == 'WCB':
					try:
						self.svgLayer_Old = int( node.get( 'layer' ) )
						self.svgNodeCount_Old = int( node.get( 'node' ) )
						self.svgLastPath_Old = int( node.get( 'lastpath' ) )
						self.svgLastPathNC_Old = int( node.get( 'lastpathnc' ) )
						self.svgLastKnownPosX_Old = float( node.get( 'lastknownposx' ) )
						self.svgLastKnownPosY_Old = float( node.get( 'lastknownposy' ) ) 
						self.svgPausedPosX_Old = float( node.get( 'pausedposx' ) )
						self.svgPausedPosY_Old = float( node.get( 'pausedposy' ) ) 
						self.svgDataRead = True
					except:
						pass

	def UpdateSVGWCBData( self, aNodeList ):
		if ( not self.svgDataRead ):
			for node in aNodeList:
				if node.tag == 'svg':
					self.UpdateSVGWCBData( node )
				elif node.tag == inkex.addNS( 'WCB', 'svg' ) or node.tag == 'WCB':
					node.set( 'layer', str( self.svgLayer ) )
					node.set( 'node', str( self.svgNodeCount ) )
					node.set( 'lastpath', str( self.svgLastPath ) )
					node.set( 'lastpathnc', str( self.svgLastPathNC ) )
					node.set( 'lastknownposx', str( (self.svgLastKnownPosX ) ) )
					node.set( 'lastknownposy', str( (self.svgLastKnownPosY ) ) )
					node.set( 'pausedposx', str( (self.svgPausedPosX) ) )
					node.set( 'pausedposy', str( (self.svgPausedPosY) ) )
					
					self.svgDataRead = True
					 
	def setupCommand( self ):
		"""Execute commands from the "setup" tab"""

		if self.serialPort is None:
			return

		self.ServoSetupWrapper()

		if self.options.setupType == "align-mode":
			self.penUp()
			ebb_motion.sendDisableMotors(self.serialPort)	

		elif self.options.setupType == "toggle-pen":
			self.ServoSetMode()
			ebb_motion.TogglePen(self.serialPort)

			
	def manualCommand( self ):
		"""Execute commands from the "manual" tab"""

		if self.options.manualType == "none":
			return
			
		if self.serialPort is None:
			return 

		if self.options.manualType == "raise-pen":
			self.ServoSetupWrapper()
			self.penUp()

		elif self.options.manualType == "lower-pen":
			self.ServoSetupWrapper()
			self.penDown()

		elif self.options.manualType == "enable-motors":
			self.EnableMotors()

		elif self.options.manualType == "disable-motors":
			ebb_motion.sendDisableMotors(self.serialPort)	

		elif self.options.manualType == "version-check":
			strVersion = ebb_serial.query( self.serialPort, 'v\r' )
			inkex.errormsg( 'I asked the EBB for its version info, and it replied:\n ' + strVersion )

		else:  # self.options.manualType is walk motor:
			if self.options.manualType == "walk-y-motor":
				nDeltaX = 0
				nDeltaY = self.options.WalkDistance
			elif self.options.manualType == "walk-x-motor":
				nDeltaY = 0
				nDeltaX = self.options.WalkDistance
			else:
				return
				
			#Query pen position: 1 up, 0 down (followed by OK)
			strVersion = ebb_serial.query( self.serialPort, 'QP\r' )
			if strVersion[0] == '0':
				self.fSpeed = self.options.penDownSpeed
			if strVersion[0] == '1':
				self.fSpeed = self.options.penUpSpeed
				
 			self.EnableMotors() #Set plotting resolution 
			self.fCurrX = self.svgLastKnownPosX_Old + axidraw_conf.F_StartPos_X
			self.fCurrY = self.svgLastKnownPosY_Old + axidraw_conf.F_StartPos_Y
			self.ignoreLimits = True
			self.fX = self.fCurrX + nDeltaX * 90  #Note: Walking motors is STRICTLY RELATIVE TO INITIAL POSITION.
			self.fY = self.fCurrY + nDeltaY * 90  
			self.plotLineAndTime(self.fX, self.fY ) 


	def MoveDeltaXY(self,xDist,yDist):  
		self.fX = self.fX + xDist   #Todo: Add limit checking?
		self.fY = self.fY + yDist 
		self.plotLineAndTime(self.fX, self.fY )  
		
	def MoveToXY(self,xPos,yPos):  
		self.fX = xPos   #Todo: Add limit checking?
		self.fY = yPos 
		self.plotLineAndTime(self.fX, self.fY )  

	def moveHome(self):
		self.xBoundsMin = axidraw_conf.F_StartPos_X
		self.yBoundsMin = axidraw_conf.F_StartPos_Y
		self.MoveToXY(axidraw_conf.F_StartPos_X, axidraw_conf.F_StartPos_Y)

	def plotToWCB( self ):
		'''Perform the actual plotting, if selected in the interface:'''
		#parse the svg data as a series of line segments and send each segment to be plotted

		if self.serialPort is None:
			return

		if (not self.getDocProps()):
			# Cannot handle the document's dimensions!!!
			inkex.errormsg( gettext.gettext(
			'This document does not have valid dimensions.\r' +
			'Consider starting with the "Letter landscape" or ' +
			'the "A4 landscape" template.\r\r' +
			'Document dimensions may also be set in Inkscape' +
			'using File > Document Properties.\r\r' +
			'The document dimensions must be in either' +
			'millimeters (mm) or inches (in).'	) )
			return

		# Viewbox handling
		# Also ignores the preserveAspectRatio attribute
		viewbox = self.svg.get( 'viewBox' )
		if viewbox:
			vinfo = viewbox.strip().replace( ',', ' ' ).split( ' ' )
			if ( vinfo[2] != 0 ) and ( vinfo[3] != 0 ):
				sx = self.svgWidth / float( vinfo[2] )
				sy = self.svgHeight / float( vinfo[3] )
# 				inkex.errormsg( 'self.svgWidth:  ' + str(self.svgWidth) )
# 				inkex.errormsg( 'float( vinfo[2] ):  ' + str(float( vinfo[2] ) ))
# 				inkex.errormsg( 'sx:  ' + str(sx) )				
				self.svgTransform = parseTransform( 'scale(%f,%f) translate(%f,%f)' % (sx, sy, -float( vinfo[0] ), -float( vinfo[1])))
# 				inkex.errormsg( 'svgTransform:  ' + str(self.svgTransform) )

		self.ServoSetup()
		self.penUp() 
		self.EnableMotors() #Set plotting resolution

		try:
			# wrap everything in a try so we can for sure close the serial port 
			self.recursivelyTraverseSvg( self.svg, self.svgTransform )
			self.penUp()   #Always end with pen-up
 
			# return to home after end of normal plot
			if ( ( not self.bStopped ) and ( self.ptFirst ) ):
				self.xBoundsMin = axidraw_conf.F_StartPos_X
				self.yBoundsMin = axidraw_conf.F_StartPos_Y
				self.fX = self.ptFirst[0]
				self.fY = self.ptFirst[1] 
 				self.nodeCount = self.nodeTarget    
				self.plotLineAndTime(self.fX, self.fY )
			if ( not self.bStopped ): 
				if (self.options.tab == '"splash"') or (self.options.tab == '"layers"') or (self.options.tab == '"resume"'):
					self.svgLayer = 0
					self.svgNodeCount = 0
					self.svgLastPath = 0
					self.svgLastPathNC = 0
					self.svgLastKnownPosX = 0
					self.svgLastKnownPosY = 0
					self.svgPausedPosX = 0
					self.svgPausedPosY = 0
					#Clear saved position data from the SVG file,
					#  IF we have completed a normal plot from the splash, layer, or resume tabs.

		finally:
			# We may have had an exception and lost the serial port...
			pass

	def recursivelyTraverseSvg( self, aNodeList,
			matCurrent=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
			parent_visibility='visible' ):
		"""
		Recursively traverse the svg file to plot out all of the
		paths.  The function keeps track of the composite transformation
		that should be applied to each path.

		This function handles path, group, line, rect, polyline, polygon,
		circle, ellipse and use (clone) elements.  Notable elements not
		handled include text.  Unhandled elements should be converted to
		paths in Inkscape.
		"""
		for node in aNodeList:
			# Ignore invisible nodes
			v = node.get( 'visibility', parent_visibility )
			if v == 'inherit':
				v = parent_visibility
			if v == 'hidden' or v == 'collapse':
				pass

			# first apply the current matrix transform to this node's transform
			matNew = composeTransform( matCurrent, parseTransform( node.get( "transform" ) ) )

			if node.tag == inkex.addNS( 'g', 'svg' ) or node.tag == 'g':

				self.penUp()
				if ( node.get( inkex.addNS( 'groupmode', 'inkscape' ) ) == 'layer' ): 
					self.DoWePlotLayer( node.get( inkex.addNS( 'label', 'inkscape' ) ) )
				self.recursivelyTraverseSvg( node, matNew, parent_visibility=v )			
			
			elif node.tag == inkex.addNS( 'use', 'svg' ) or node.tag == 'use':

				# A <use> element refers to another SVG element via an xlink:href="#blah"
				# attribute.  We will handle the element by doing an XPath search through
				# the document, looking for the element with the matching id="blah"
				# attribute.  We then recursively process that element after applying
				# any necessary (x,y) translation.
				#
				# Notes:
				#  1. We ignore the height and width attributes as they do not apply to
				#     path-like elements, and
				#  2. Even if the use element has visibility="hidden", SVG still calls
				#     for processing the referenced element.  The referenced element is
				#     hidden only if its visibility is "inherit" or "hidden".

				refid = node.get( inkex.addNS( 'href', 'xlink' ) )
				if refid:
					# [1:] to ignore leading '#' in reference
					path = '//*[@id="%s"]' % refid[1:]
					refnode = node.xpath( path )
					if refnode:
						x = float( node.get( 'x', '0' ) )
						y = float( node.get( 'y', '0' ) )
						# Note: the transform has already been applied
						if ( x != 0 ) or (y != 0 ):
							matNew2 = composeTransform( matNew, parseTransform( 'translate(%f,%f)' % (x,y) ) )
						else:
							matNew2 = matNew
						v = node.get( 'visibility', v )
						self.recursivelyTraverseSvg( refnode, matNew2, parent_visibility=v )
					else:
						pass
				else:
					pass

			elif node.tag == inkex.addNS( 'path', 'svg' ):

				# if we're in resume mode AND self.pathcount < self.svgLastPath,
				#    then skip over this path.
				# if we're in resume mode and self.pathcount = self.svgLastPath,
				#    then start here, and set self.nodeCount equal to self.svgLastPathNC
				
				doWePlotThisPath = False 
				if (self.resumeMode): 
					if (self.pathcount < self.svgLastPath_Old ): 
						#This path was *completely plotted* already; skip.
						self.pathcount += 1 
					elif (self.pathcount == self.svgLastPath_Old ): 
						#this path is the first *not completely* plotted path:
						self.nodeCount =  self.svgLastPathNC_Old	#Nodecount after last completed path
						doWePlotThisPath = True 
				else:
					doWePlotThisPath = True
				if (doWePlotThisPath):
					self.pathcount += 1
					self.plotPath( node, matNew )
				
			elif node.tag == inkex.addNS( 'rect', 'svg' ) or node.tag == 'rect':

				# Manually transform 
				#    <rect x="X" y="Y" width="W" height="H"/> 
				# into 
				#    <path d="MX,Y lW,0 l0,H l-W,0 z"/> 
				# I.e., explicitly draw three sides of the rectangle and the
				# fourth side implicitly

				 
				# if we're in resume mode AND self.pathcount < self.svgLastPath,
				#    then skip over this path.
				# if we're in resume mode and self.pathcount = self.svgLastPath,
				#    then start here, and set
				# self.nodeCount equal to self.svgLastPathNC
				
				doWePlotThisPath = False 
				if (self.resumeMode): 
					if (self.pathcount < self.svgLastPath_Old ): 
						#This path was *completely plotted* already; skip.
						self.pathcount += 1 
					elif (self.pathcount == self.svgLastPath_Old ): 
						#this path is the first *not completely* plotted path:
						self.nodeCount =  self.svgLastPathNC_Old	#Nodecount after last completed path
						doWePlotThisPath = True 
				else:
					doWePlotThisPath = True
				if (doWePlotThisPath):
					self.pathcount += 1
					# Create a path with the outline of the rectangle
					newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
					x = float( node.get( 'x' ) )
					y = float( node.get( 'y' ) )
					w = float( node.get( 'width' ) )
					h = float( node.get( 'height' ) )
					s = node.get( 'style' )
					if s:
						newpath.set( 'style', s )
					t = node.get( 'transform' )
					if t:
						newpath.set( 'transform', t )
					a = []
					a.append( ['M ', [x, y]] )
					a.append( [' l ', [w, 0]] )
					a.append( [' l ', [0, h]] )
					a.append( [' l ', [-w, 0]] )
					a.append( [' Z', []] )
					newpath.set( 'd', simplepath.formatPath( a ) )
					self.plotPath( newpath, matNew )
					
			elif node.tag == inkex.addNS( 'line', 'svg' ) or node.tag == 'line':

				# Convert
				#
				#   <line x1="X1" y1="Y1" x2="X2" y2="Y2/>
				#
				# to
				#
				#   <path d="MX1,Y1 LX2,Y2"/>

				# if we're in resume mode AND self.pathcount < self.svgLastPath,
				#    then skip over this path.
				# if we're in resume mode and self.pathcount = self.svgLastPath,
				#    then start here, and set
				# self.nodeCount equal to self.svgLastPathNC

				doWePlotThisPath = False 
				if (self.resumeMode): 
					if (self.pathcount < self.svgLastPath_Old ): 
						#This path was *completely plotted* already; skip.
						self.pathcount += 1 
					elif (self.pathcount == self.svgLastPath_Old ): 
						#this path is the first *not completely* plotted path:
						self.nodeCount =  self.svgLastPathNC_Old	#Nodecount after last completed path
						doWePlotThisPath = True 
				else:
					doWePlotThisPath = True
				if (doWePlotThisPath):
					self.pathcount += 1
					# Create a path to contain the line
					newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
					x1 = float( node.get( 'x1' ) )
					y1 = float( node.get( 'y1' ) )
					x2 = float( node.get( 'x2' ) )
					y2 = float( node.get( 'y2' ) )
					s = node.get( 'style' )
					if s:
						newpath.set( 'style', s )
					t = node.get( 'transform' )
					if t:
						newpath.set( 'transform', t )
					a = []
					a.append( ['M ', [x1, y1]] )
					a.append( [' L ', [x2, y2]] )
					newpath.set( 'd', simplepath.formatPath( a ) )
					self.plotPath( newpath, matNew )
					

			elif node.tag == inkex.addNS( 'polyline', 'svg' ) or node.tag == 'polyline':

				# Convert
				#  <polyline points="x1,y1 x2,y2 x3,y3 [...]"/> 
				# to 
				#   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...]"/> 
				# Note: we ignore polylines with no points

				pl = node.get( 'points', '' ).strip()
				if pl == '':
					pass

				#if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
				#if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
				# self.nodeCount equal to self.svgLastPathNC
				
				doWePlotThisPath = False 
				if (self.resumeMode): 
					if (self.pathcount < self.svgLastPath_Old ): 
						#This path was *completely plotted* already; skip.
						self.pathcount += 1 
					elif (self.pathcount == self.svgLastPath_Old ): 
						#this path is the first *not completely* plotted path:
						self.nodeCount =  self.svgLastPathNC_Old	#Nodecount after last completed path
						doWePlotThisPath = True 
				else:
					doWePlotThisPath = True
				if (doWePlotThisPath):
					self.pathcount += 1
					
					pa = pl.split()
					if not len( pa ):
						pass
					# Issue 29: pre 2.5.? versions of Python do not have
					#    "statement-1 if expression-1 else statement-2"
					# which came out of PEP 308, Conditional Expressions
					#d = "".join( ["M " + pa[i] if i == 0 else " L " + pa[i] for i in range( 0, len( pa ) )] )
					d = "M " + pa[0]
					for i in range( 1, len( pa ) ):
						d += " L " + pa[i]
					newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
					newpath.set( 'd', d );
					s = node.get( 'style' )
					if s:
						newpath.set( 'style', s )
					t = node.get( 'transform' )
					if t:
						newpath.set( 'transform', t )
					self.plotPath( newpath, matNew )

			elif node.tag == inkex.addNS( 'polygon', 'svg' ) or node.tag == 'polygon':

				# Convert 
				#  <polygon points="x1,y1 x2,y2 x3,y3 [...]"/> 
				# to 
				#   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...] Z"/> 
				# Note: we ignore polygons with no points

				pl = node.get( 'points', '' ).strip()
				if pl == '':
					pass

				#if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
				#if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
				# self.nodeCount equal to self.svgLastPathNC

				doWePlotThisPath = False 
				if (self.resumeMode): 
					if (self.pathcount < self.svgLastPath_Old ): 
						#This path was *completely plotted* already; skip.
						self.pathcount += 1 
					elif (self.pathcount == self.svgLastPath_Old ): 
						#this path is the first *not completely* plotted path:
						self.nodeCount =  self.svgLastPathNC_Old	#Nodecount after last completed path
						doWePlotThisPath = True 
				else:
					doWePlotThisPath = True
				if (doWePlotThisPath):
					self.pathcount += 1
					
					pa = pl.split()
					if not len( pa ):
						pass
					# Issue 29: pre 2.5.? versions of Python do not have
					#    "statement-1 if expression-1 else statement-2"
					# which came out of PEP 308, Conditional Expressions
					#d = "".join( ["M " + pa[i] if i == 0 else " L " + pa[i] for i in range( 0, len( pa ) )] )
					d = "M " + pa[0]
					for i in range( 1, len( pa ) ):
						d += " L " + pa[i]
					d += " Z"
					newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
					newpath.set( 'd', d );
					s = node.get( 'style' )
					if s:
						newpath.set( 'style', s )
					t = node.get( 'transform' )
					if t:
						newpath.set( 'transform', t )
					self.plotPath( newpath, matNew )
					
			elif node.tag == inkex.addNS( 'ellipse', 'svg' ) or \
				node.tag == 'ellipse' or \
				node.tag == inkex.addNS( 'circle', 'svg' ) or \
				node.tag == 'circle':

					# Convert circles and ellipses to a path with two 180 degree arcs.
					# In general (an ellipse), we convert 
					#   <ellipse rx="RX" ry="RY" cx="X" cy="Y"/> 
					# to 
					#   <path d="MX1,CY A RX,RY 0 1 0 X2,CY A RX,RY 0 1 0 X1,CY"/> 
					# where 
					#   X1 = CX - RX
					#   X2 = CX + RX 
					# Note: ellipses or circles with a radius attribute of value 0 are ignored

					if node.tag == inkex.addNS( 'ellipse', 'svg' ) or node.tag == 'ellipse':
						rx = float( node.get( 'rx', '0' ) )
						ry = float( node.get( 'ry', '0' ) )
					else:
						rx = float( node.get( 'r', '0' ) )
						ry = rx
					if rx == 0 or ry == 0:
						pass

					
					#if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
					#if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
					# self.nodeCount equal to self.svgLastPathNC
					
					doWePlotThisPath = False 
					if (self.resumeMode): 
						if (self.pathcount < self.svgLastPath_Old ): 
							#This path was *completely plotted* already; skip.
							self.pathcount += 1 
						elif (self.pathcount == self.svgLastPath_Old ): 
							#this path is the first *not completely* plotted path:
							self.nodeCount =  self.svgLastPathNC_Old	#Nodecount after last completed path
							doWePlotThisPath = True 
					else:
						doWePlotThisPath = True
					if (doWePlotThisPath):
						self.pathcount += 1
					
						cx = float( node.get( 'cx', '0' ) )
						cy = float( node.get( 'cy', '0' ) )
						x1 = cx - rx
						x2 = cx + rx
						d = 'M %f,%f ' % ( x1, cy ) + \
							'A %f,%f ' % ( rx, ry ) + \
							'0 1 0 %f,%f ' % ( x2, cy ) + \
							'A %f,%f ' % ( rx, ry ) + \
							'0 1 0 %f,%f' % ( x1, cy )
						newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
						newpath.set( 'd', d );
						s = node.get( 'style' )
						if s:
							newpath.set( 'style', s )
						t = node.get( 'transform' )
						if t:
							newpath.set( 'transform', t )
						self.plotPath( newpath, matNew )
						
							
			elif node.tag == inkex.addNS( 'metadata', 'svg' ) or node.tag == 'metadata':
				pass
			elif node.tag == inkex.addNS( 'defs', 'svg' ) or node.tag == 'defs':
				pass
			elif node.tag == inkex.addNS( 'namedview', 'sodipodi' ) or node.tag == 'namedview':
				pass
			elif node.tag == inkex.addNS( 'WCB', 'svg' ) or node.tag == 'WCB':
				pass
			elif node.tag == inkex.addNS( 'eggbot', 'svg' ) or node.tag == 'eggbot':
				pass			
			elif node.tag == inkex.addNS( 'title', 'svg' ) or node.tag == 'title':
				pass
			elif node.tag == inkex.addNS( 'desc', 'svg' ) or node.tag == 'desc':
				pass
			elif node.tag == inkex.addNS( 'text', 'svg' ) or node.tag == 'text':
				if not self.warnings.has_key( 'text' ):
					inkex.errormsg( gettext.gettext( 'Warning: unable to draw text; ' +
						'please convert it to a path first.  Consider using the ' +
						'Hershey Text extension which is located under the '+
						'"Render" category of extensions.' ) )
					self.warnings['text'] = 1
				pass
			elif node.tag == inkex.addNS( 'image', 'svg' ) or node.tag == 'image':
				if not self.warnings.has_key( 'image' ):
					inkex.errormsg( gettext.gettext( 'Warning: unable to draw bitmap images; ' +
						'please convert them to line art first. Consider using the "Trace bitmap..." ' +
						'tool of the "Path" menu.  Mac users please note that some X11 settings may ' +
						'cause cut-and-paste operations to paste in bitmap copies.' ) )
					self.warnings['image'] = 1
				pass
			elif node.tag == inkex.addNS( 'pattern', 'svg' ) or node.tag == 'pattern':
				pass
			elif node.tag == inkex.addNS( 'radialGradient', 'svg' ) or node.tag == 'radialGradient':
				# Similar to pattern
				pass
			elif node.tag == inkex.addNS( 'linearGradient', 'svg' ) or node.tag == 'linearGradient':
				# Similar in pattern
				pass
			elif node.tag == inkex.addNS( 'style', 'svg' ) or node.tag == 'style':
				# This is a reference to an external style sheet and not the value
				# of a style attribute to be inherited by child elements
				pass
			elif node.tag == inkex.addNS( 'cursor', 'svg' ) or node.tag == 'cursor':
				pass
			elif node.tag == inkex.addNS( 'color-profile', 'svg' ) or node.tag == 'color-profile':
				# Gamma curves, color temp, etc. are not relevant to single color output
				pass
			elif not isinstance( node.tag, basestring ):
				# This is likely an XML processing instruction such as an XML
				# comment.  lxml uses a function reference for such node tags
				# and as such the node tag is likely not a printable string.
				# Further, converting it to a printable string likely won't
				# be very useful.
				pass
			else:
				if not self.warnings.has_key( str( node.tag ) ):
					t = str( node.tag ).split( '}' )
					inkex.errormsg( gettext.gettext( 'Warning: unable to draw <' + str( t[-1] ) +
						'> object, please convert it to a path first.' ) )
					self.warnings[str( node.tag )] = 1
				pass

	def DoWePlotLayer( self, strLayerName ):
		"""
			 
		First: scan first 4 chars of node id for first non-numeric character,
		and scan the part before that (if any) into a number
		Then, see if the number matches the layer.
		"""

		# Look at layer name.  Sample first character, then first two, and
		# so on, until the string ends or the string no longer consists of digit characters only.
		
		TempNumString = 'x'
		stringPos = 1	
		layerNameInt = -1
		layerMatch = False	
		self.plotCurrentLayer = True    #Temporarily assume that we are plotting the layer
		CurrentLayerName = string.lstrip( strLayerName ) #remove leading whitespace
		MaxLength = len( CurrentLayerName )
		if MaxLength > 0:
			while stringPos <= MaxLength:
				if str.isdigit( CurrentLayerName[:stringPos] ):
					TempNumString = CurrentLayerName[:stringPos] # Store longest numeric string so far
					stringPos = stringPos + 1
				else:
					break

		if ( str.isdigit( TempNumString ) ):
			layerNameInt = int( float( TempNumString ) )
			if ( self.svgLayer == layerNameInt ):
				layerMatch = True	#Match! The current layer IS named in the Layers tab.
			
		if ((self.PrintFromLayersTab) and (layerMatch == False)):
			self.plotCurrentLayer = False

		if (self.plotCurrentLayer == True):
			self.LayersFoundToPlot = True

	def plotPath( self, path, matTransform ):
		'''
		Plot the path while applying the transformation defined
		by the matrix [matTransform].
		'''
		# turn this path into a cubicsuperpath (list of beziers)...

		d = path.get( 'd' )
		if len( simplepath.parsePath( d ) ) == 0:
			return

		if self.plotCurrentLayer:

			# reset page bounds for plotting:
			self.xBoundsMax = axidraw_conf.N_PAGE_WIDTH
			self.xBoundsMin = 0
			self.yBoundsMax = axidraw_conf.N_PAGE_HEIGHT
			self.yBoundsMin = 0
	
			p = cubicsuperpath.parsePath( d )
	
			# ...and apply the transformation to each point
			applyTransformToPath( matTransform, p )
	
			# p is now a list of lists of cubic beziers [control pt1, control pt2, endpoint]
			# where the start-point is the last point in the previous segment.
			for sp in p:
			
				plot_utils.subdivideCubicPath( sp, self.options.smoothness )
				nIndex = 0
	
				for csp in sp:
	
					if self.bStopped:
						return
	
					if self.plotCurrentLayer:
						if nIndex == 0:
							self.penUp()
							self.virtualPenIsUp = True
						elif nIndex == 1:
							self.penDown()
							self.virtualPenIsUp = False
	
					nIndex += 1
	
					self.fX = float( csp[1][0] )    # Set move destination
					self.fY = float( csp[1][1] )  
					
					self.plotLineAndTime(self.fX, self.fY )   #Draw a segment
						
			if ( not self.bStopped ):	#an "index" for resuming plots quickly-- record last complete path
				self.svgLastPath = self.pathcount #The number of the last path completed
				self.svgLastPathNC = self.nodeCount #the node count after the last path was completed.			
			

	def plotLineAndTime( self, xDest, yDest ):
		'''
		Send commands out the com port as a line segment (dx, dy) and a time (ms) the segment
		should take to implement.  
		Important note: Everything up to this point uses *pixel* scale. 
		Here, we convert from floating-point pixel scale to actual motor steps, w/ present DPI.
		'''
		
		if (self.ignoreLimits == False):
			if (xDest > self.xBoundsMax):	#Check machine size limit; truncate at edges
				xDest = self.xBoundsMax
			if (xDest < self.xBoundsMin):	#Check machine size limit; truncate at edges
				xDest = self.xBoundsMin			
			if (yDest > self.yBoundsMax):	#Check machine size limit; truncate at edges
				yDest = self.yBoundsMax
			if (yDest < self.yBoundsMin):	#Check machine size limit; truncate at edges
				yDest = self.yBoundsMin
			
		if self.bStopped:
			return
		if ( self.fCurrX is None ):
			return

		xTemp = self.stepsPerInch * ( xDest - self.fCurrX ) + self.xErr
		yTemp = self.stepsPerInch * ( yDest - self.fCurrY ) + self.yErr

		nDeltaX = int (round(xTemp)) # Number of motor steps required
		nDeltaY = int (round(yTemp)) 

		self.xErr = xTemp - float(nDeltaX)  # Keep track of rounding errors, so that they do not accumulate.
		self.yErr = yTemp - float(nDeltaY)

		plotDistance = plot_utils.distance( nDeltaX, nDeltaY )

		if (plotDistance >= 1 ):	# if at least one motor step is required for this move....
			self.nodeCount += 1

			if self.bPenIsUp:
				self.fSpeed = self.BrushUpSpeed
				if (plotDistance > (self.RapidThreshold * self.stepsPerInch)):
					self.fSpeed = self.BrushRapidSpeed
			else:
				self.fSpeed = self.BrushDownSpeed


			if self.resumeMode:
				if ( self.nodeCount >= self.nodeTarget ):
					self.resumeMode = False
					self.paintdist = 0

					if ( not self.virtualPenIsUp ):
						self.penDown()
						self.fSpeed = self.BrushDownSpeed

			nTime =  10000.00 / self.fSpeed * plotDistance
# 			nTime =  10000.00 / self.fSpeed * plot_utils.distance( nDeltaX, nDeltaY )
			nTime = int( math.ceil(nTime / 10.0))

			xd = nDeltaX
			yd = nDeltaY
			td = nTime
			if ( td < 1 ):
				td = 1		# don't allow zero-time moves.

			if (abs((float(xd) / float(td))) < 0.002):	
				xd = 0	#don't allow too-slow movements of this axis
			if (abs((float(yd) / float(td))) < 0.002):	
				yd = 0	#don't allow too-slow movements of this axis

			if (not self.resumeMode) and (not self.bStopped):
				if ( self.options.revMotor1 ):
					xd2 = -xd
				else:
					xd2 = xd
				if ( self.options.revMotor2):
					yd2 = -yd
				else:
					yd2 = yd 
				
				#TODO: Test that these motor 1 and motor 2 assignments match up to the controls in the inx file.	
					
				ebb_motion.doABMove( self.serialPort, xd2, yd2, td )			
				if (td > 50):
					if self.options.tab != '"manual"':
						time.sleep(float(td - 50)/1000.0)  #pause before issuing next command
				self.fCurrX += xd / self.stepsPerInch   # Update current position
				self.fCurrY += yd / self.stepsPerInch		

				self.svgLastKnownPosX = self.fCurrX - axidraw_conf.F_StartPos_X
				self.svgLastKnownPosY = self.fCurrY - axidraw_conf.F_StartPos_Y	

			strButton = ebb_motion.QueryPRGButton(self.serialPort)	#Query if button pressed
			if strButton[0] == '1': #button pressed
				self.svgNodeCount = self.nodeCount;
				self.svgPausedPosX = self.fCurrX - axidraw_conf.F_StartPos_X	#self.svgLastKnownPosX
				self.svgPausedPosY = self.fCurrY - axidraw_conf.F_StartPos_Y	#self.svgLastKnownPosY
				inkex.errormsg( 'Plot paused by button press after node number ' + str( self.nodeCount ) + '.' )
				inkex.errormsg( 'Use the "resume" feature to continue.' )
				self.bStopped = True
				return

	def EnableMotors( self ):
		if ( self.options.resolution == 1 ):
			ebb_motion.sendEnableMotors(self.serialPort, 1) # 16X microstepping
			self.stepsPerInch = float( axidraw_conf.F_DPI_16X)
			self.BrushUpSpeed   = self.options.penUpSpeed * axidraw_conf.F_Speed_Scale
			self.BrushDownSpeed = self.options.penDownSpeed * axidraw_conf.F_Speed_Scale
			self.BrushRapidSpeed = self.options.rapidSpeed * axidraw_conf.F_Speed_Scale
		elif ( self.options.resolution == 2 ):
			ebb_motion.sendEnableMotors(self.serialPort, 2) # 8X microstepping
			self.stepsPerInch = float( axidraw_conf.F_DPI_16X / 2.0 )  
			self.BrushUpSpeed   = self.options.penUpSpeed * axidraw_conf.F_Speed_Scale / 2
			self.BrushDownSpeed = self.options.penDownSpeed * axidraw_conf.F_Speed_Scale / 2
			self.BrushRapidSpeed = self.options.rapidSpeed * axidraw_conf.F_Speed_Scale /2
		else:
			ebb_motion.sendEnableMotors(self.serialPort, 3) # 4X microstepping  
			self.stepsPerInch = float( axidraw_conf.F_DPI_16X / 4.0 )
			self.BrushUpSpeed   = self.options.penUpSpeed * axidraw_conf.F_Speed_Scale / 4
			self.BrushDownSpeed = self.options.penDownSpeed * axidraw_conf.F_Speed_Scale / 4
			self.BrushRapidSpeed = self.options.rapidSpeed * axidraw_conf.F_Speed_Scale /4

	def penUp( self ):
		self.virtualPenIsUp = True  # Virtual pen keeps track of state for resuming plotting.
		if ( not self.resumeMode) and (not self.bPenIsUp):	# skip if pen is already up, or if we're resuming.
			ebb_motion.sendPenUp(self.serialPort, self.options.penUpDelay )				
			self.bPenIsUp = True

	def penDown( self ):
		self.virtualPenIsUp = False  # Virtual pen keeps track of state for resuming plotting.
		if (self.bPenIsUp != False):  # skip if pen is already down
			if ((not self.resumeMode) and ( not self.bStopped )): #skip if resuming or stopped
				self.ServoSetMode()
				ebb_motion.sendPenDown(self.serialPort, self.options.penUpDelay )						
				self.bPenIsUp = False

	def ServoSetupWrapper( self ):
		# Assert what the defined "up" and "down" positions of the servo motor should be,
		#    and determine what the pen state is.
		self.ServoSetup()
		strVersion = ebb_serial.query( self.serialPort, 'QP\r' )
		if strVersion[0] == '0':
			self.bPenIsUp = False
		else:
			self.bPenIsUp = True

	def ServoSetup( self ):
		''' Pen position units range from 0% to 100%, which correspond to
		    a typical timing range of 7500 - 25000 in units of 1/(12 MHz).
		    1% corresponds to ~14.6 us, or 175 units of 1/(12 MHz).
		'''
		
		servo_range = axidraw_conf.SERVO_MAX - axidraw_conf.SERVO_MIN
		servo_slope = float(servo_range) / 100
		
		intTemp = axidraw_conf.SERVO_MIN + servo_slope * self.options.penUpPosition
		ebb_serial.command( self.serialPort,  'SC,4,' + str( intTemp ) + '\r' )	
				
		intTemp = axidraw_conf.SERVO_MIN + servo_slope * self.options.penDownPosition
		ebb_serial.command( self.serialPort,  'SC,5,' + str( intTemp ) + '\r' )

		''' Servo speed units are in units of %/second, referring to the
			percentages above.  The EBB takes speeds in units of 1/(12 MHz) steps
			per 21 ms.  Scaling as above, 1% in 1 second corresponds to
			175 steps/s, or 0.175 steps/ms, which corresponds
			to ~3.6 steps/21 ms.  Rounding this to 4 steps/21 ms is sufficient.		'''
		
		intTemp = 4 * self.options.ServoUpSpeed
		ebb_serial.command( self.serialPort, 'SC,11,' + str( intTemp ) + '\r' )

		intTemp = 4 * self.options.ServoDownSpeed
		ebb_serial.command( self.serialPort,  'SC,12,' + str( intTemp ) + '\r' )
		
	def ServoSetMode (self):
		intTemp = 7500 + 175 * self.options.penDownPosition
		ebb_serial.command( self.serialPort,  'SC,5,' + str( intTemp ) + '\r' )		

	def stop( self ):
		self.bStopped = True

	def getDocProps( self ):
		'''
		Get the document's height and width attributes from the <svg> tag.
		Use a default value in case the property is not present or is
		expressed in units of percentages.
		'''
		self.svgHeight = plot_utils.getLengthInches( self, 'height' )
		self.svgWidth = plot_utils.getLengthInches( self, 'width' )
		if ( self.svgHeight == None ) or ( self.svgWidth == None ):
			return False
		else:
			self.RapidThreshold = float(self.svgHeight) * 0.1 
			return True

e = WCB()
#e.affect(output=False)
e.affect()
