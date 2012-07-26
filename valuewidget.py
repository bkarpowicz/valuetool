"""
/***************************************************************************
         Value Tool       - A QGIS plugin to get values at the mouse pointer
                             -------------------
    begin                : 2008-08-26
    copyright            : (C) 2008 by G. Picard
    email                : 
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

import logging
# change the level back to logging.WARNING(the default) before releasing
logging.basicConfig(level=logging.DEBUG)

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

hasqwt=True
try:
    from PyQt4.Qwt5 import QwtPlot,QwtPlotCurve,QwtScaleDiv,QwtSymbol
except:
    hasqwt=False

#test if matplotlib >= 1.0
hasmpl=True
try:
    import matplotlib
    import matplotlib.pyplot as plt 
    import matplotlib.ticker as ticker
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
except:
    hasmpl=False
if hasmpl:
    if int(matplotlib.__version__[0]) < 1:
        hasmpl = False

class ValueWidget(QWidget):

    def __init__(self, iface):

        self.hasqwt=hasqwt
        self.hasmpl=hasmpl
        self.layerMap=dict()
        self.iface=iface
        self.canvas=self.iface.mapCanvas()
        self.logger = logging.getLogger('.'.join((__name__, 
                                        self.__class__.__name__)))

        QWidget.__init__(self)
        self.setupUi()

        QObject.connect(self.checkBox_2,SIGNAL("stateChanged(int)"),self.changeActive)
        #self.changeActive(Qt.Checked)
        #set inactive by default - should save last state in user config
        self.checkBox_2.setCheckState(Qt.Unchecked)
        QObject.connect(self.checkBox,SIGNAL("stateChanged(int)"),self.changePage)
        QObject.connect(self.canvas, SIGNAL( "keyPressed( QKeyEvent * )" ), self.pauseDisplay )
        QObject.connect(self.plotSelector, SIGNAL( "currentIndexChanged ( int )" ), self.changePlot )


        if (self.hasqwt):
            self.curve = QwtPlotCurve()
            self.curve.setSymbol(
                QwtSymbol(QwtSymbol.Ellipse,
                          QBrush(Qt.white),
                          QPen(Qt.red, 2),
                          QSize(9, 9)))
            self.curve.attach(self.qwtPlot)

    def setupUi(self):

        self.vboxlayout = QtGui.QVBoxLayout(self)
        self.vboxlayout.setObjectName("vboxlayout")

        self.hboxlayout = QtGui.QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")

        # active
        self.checkBox_2 = QtGui.QCheckBox()
        self.checkBox_2.setChecked(True)
        self.checkBox_2.setObjectName("checkBox_2")
        self.hboxlayout.addWidget(self.checkBox_2)
        self.separator = QtGui.QFrame()
        self.separator.setFrameStyle( QtGui.QFrame.VLine | QtGui.QFrame.Sunken )
        self.hboxlayout.addWidget(self.separator)

        # graph
        self.checkBox = QtGui.QCheckBox()
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.checkBox.sizePolicy().hasHeightForWidth())
        self.checkBox.setSizePolicy(sizePolicy)
        self.checkBox.setObjectName("checkBox")
        self.hboxlayout.addWidget(self.checkBox)

        self.plotSelector = QtGui.QComboBox()
        if self.hasqwt:
            self.plotSelector.addItem( 'Qwt' )
        if self.hasmpl:
            self.plotSelector.addItem( 'matplotlib' )
        self.plotSelector.setCurrentIndex( 0 );
        if (not self.hasqwt or not self.hasmpl):
            #self.plotSelector.setVisible(False)
            self.plotSelector.setEnabled(False)

        self.hboxlayout.addWidget(self.plotSelector)
                
        spacerItem = QtGui.QSpacerItem(40,15,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem)
        self.vboxlayout.addLayout(self.hboxlayout)

        self.stackedWidget = QtGui.QStackedWidget()

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.stackedWidget.setSizePolicy(sizePolicy)
        self.stackedWidget.setObjectName("stackedWidget")

        # Page 1
        self.tableWidget = QtGui.QTableWidget(self.stackedWidget)
        self.tableWidget.setObjectName("tableWidget")
        self.stackedWidget.addWidget(self.tableWidget)

        #Page 2
        if self.hasqwt:
            self.qwtPlot = QwtPlot(self.stackedWidget)
            self.qwtPlot.setAutoFillBackground(False)
            self.qwtPlot.setObjectName("qwtPlot")
        else:
            self.qwtPlot = QtGui.QLabel("Need Qwt >= 5.0 or matplotlib >= 1.0 !")

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.qwtPlot.sizePolicy().hasHeightForWidth())
        self.qwtPlot.setSizePolicy(sizePolicy)
        self.qwtPlot.setObjectName("qwtPlot")
        self.qwtPlot.updateGeometry()
        self.stackedWidget.addWidget(self.qwtPlot)

        #Page 3 - matplotlib
        if self.hasmpl:
            # mpl stuff
            # should make figure light gray
            self.mplLine = None #make sure to invalidate when layers change
            self.mplBackground = None #http://www.scipy.org/Cookbook/Matplotlib/Animations
            self.mplFig = plt.Figure(facecolor='w', edgecolor='w')
            self.mplFig.subplots_adjust(left=0.1, right=0.975, bottom=0.13, top=0.95)
            self.mplPlt = self.mplFig.add_subplot(111)   
            self.mplPlt.tick_params(axis='both', which='major', labelsize=12)
            self.mplPlt.tick_params(axis='both', which='minor', labelsize=10)                           
            # qt stuff
            self.pltCanvas = FigureCanvasQTAgg(self.mplFig)
            self.pltCanvas.setParent(self.stackedWidget)
            self.pltCanvas.setAutoFillBackground(False)
            self.pltCanvas.setObjectName("mplPlot")
            self.mplPlot = self.pltCanvas
        else:
            self.mplPlot = QtGui.QLabel("Need Qwt >= 5.0 or matplotlib >= 1.0 !")

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.mplPlot.sizePolicy().hasHeightForWidth())
        self.mplPlot.setSizePolicy(sizePolicy)
        self.qwtPlot.setObjectName("qwtPlot")
        self.mplPlot.updateGeometry()
        self.stackedWidget.addWidget(self.mplPlot)

        self.vboxlayout.addWidget(self.stackedWidget)

        self.retranslateUi()
        self.stackedWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateUi(self):
        self.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.checkBox_2.setText(QtGui.QApplication.translate("Form", "Active", None, QtGui.QApplication.UnicodeUTF8))
        self.checkBox_2.setToolTip(QtGui.QApplication.translate("Form", "(Shift+A) to toggle", None, QtGui.QApplication.UnicodeUTF8))
        self.checkBox.setText(QtGui.QApplication.translate("Form", "Graph", None, QtGui.QApplication.UnicodeUTF8))
        self.tableWidget.clear()
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setRowCount(0)

        headerItem = QtGui.QTableWidgetItem()
        headerItem.setText(QtGui.QApplication.translate("Form", "Layer", None, QtGui.QApplication.UnicodeUTF8))
        self.tableWidget.setHorizontalHeaderItem(0,headerItem)

        headerItem1 = QtGui.QTableWidgetItem()
        headerItem1.setText(QtGui.QApplication.translate("Form", "Value", None, QtGui.QApplication.UnicodeUTF8))
        self.tableWidget.setHorizontalHeaderItem(1,headerItem1)


    def disconnect(self):
        self.changeActive(False)
        QObject.disconnect(self.canvas, SIGNAL( "keyPressed( QKeyEvent * )" ), self.pauseDisplay )
    
    def pauseDisplay(self,e):
      if ( e.modifiers() == Qt.ShiftModifier or e.modifiers() == Qt.MetaModifier ) and e.key() == Qt.Key_A:

        self.checkBox_2.toggle()
        return True
      return False


    def keyPressEvent( self, e ):
      if ( e.modifiers() == Qt.ControlModifier or e.modifiers() == Qt.MetaModifier ) and e.key() == Qt.Key_C:
        items = QString()
        for rec in range( self.tableWidget.rowCount() ):
          items.append( '"' + self.tableWidget.item( rec, 0 ).text() + '",' + self.tableWidget.item( rec, 1 ).text() + "\n" )
        if not items.isEmpty():
          clipboard = QApplication.clipboard()
          clipboard.setText( items )
      elif (self.pauseDisplay(e)):
        pass
      else:
        QWidget.keyPressEvent( self, e )


    def changePage(self,state):
        if (state==Qt.Checked):
            if (self.plotSelector.currentText()=='matplotlib'):
                self.stackedWidget.setCurrentIndex(2)
            else:
                self.stackedWidget.setCurrentIndex(1)
        else:
            self.stackedWidget.setCurrentIndex(0)

    def changePlot(self):
        self.changePage(self.checkBox_2.checkState())

    def changeActive(self,state):
        if (state==Qt.Checked):
            if int(QGis.QGIS_VERSION[2]) > 2: # for QGIS >= 1.3
                QObject.connect(self.canvas, SIGNAL("xyCoordinates(const QgsPoint &)"), self.printValue)
            else:
                QObject.connect(self.canvas, SIGNAL("xyCoordinates(QgsPoint &)"), self.printValue)
        else:
            if int(QGis.QGIS_VERSION[2]) > 2: # for QGIS >= 1.3
                QObject.disconnect(self.canvas, SIGNAL("xyCoordinates(const QgsPoint &)"), self.printValue)
            else:
                QObject.disconnect(self.canvas, SIGNAL("xyCoordinates(QgsPoint &)"), self.printValue)


    def printValue(self,position):

        if self.canvas.layerCount() == 0:
            return
        
        needextremum = self.checkBox.isChecked() # if plot is checked

        # count the number of requires rows and remember the raster layers
        nrow=0
        rasterlayers=[]
        layersWOStatistics=[]

        for i in range(self.canvas.layerCount()):
            layer = self.canvas.layer(i)
            if (layer!=None and layer.isValid() and layer.type()==QgsMapLayer.RasterLayer):
              if layer.providerKey()=="wms":
                continue

              if layer.providerKey()=="grassraster":
                nrow+=1
                rasterlayers.append(layer)
              else: # normal raster layer
                nrow+=layer.bandCount()
                rasterlayers.append(layer)
                
              # check statistics for each band
              if needextremum:
                for i in range( 1,layer.bandCount()+1 ):
                  if not layer.id() in self.layerMap and not layer.hasStatistics(i)\
                          and not layer in layersWOStatistics:
                    layersWOStatistics.append(layer)

        if layersWOStatistics:
          self.calculateStatistics(layersWOStatistics)
                  
        # create the row if necessary
        self.tableWidget.setRowCount(nrow)

        irow=0
        self.values=[]
        self.ymin=1e38
        self.ymax=-1e38

        mapCanvasSrs = self.iface.mapCanvas().mapRenderer().destinationSrs()

        # TODO - calculate the min/max values only once, instead of every time!!!
        # keep them in a dict() with key=layer.id()
        for layer in rasterlayers:
            layerSrs = layer.srs()
            pos = position
            if not mapCanvasSrs == layerSrs and self.iface.mapCanvas().hasCrsTransformEnabled():
              srsTransform = QgsCoordinateTransform(mapCanvasSrs, layerSrs)
              try:
                pos = srsTransform.transform(position)
              except QgsCsException, err:
                # ignore transformation errors
                continue
            isok,ident = layer.identify(pos)
            if not isok:
                continue

            layername=unicode(layer.name())
            
            if layer.providerKey()=="grassraster":
              if not ident.has_key(QString("value")):
                continue
              cstr = ident[QString("value")]
              if cstr.isNull():
                continue
              value = cstr.toDouble()
              if not value[1]:
                # if this is not a double, it is probably a (GRASS string like
                # 'out of extent' or 'null (no data)'. Let's just show that:
                self.values.append((layername, cstr))
                continue
              self.values.append((layername,cstr))
              if needextremum:
                self.ymin = min(self.ymin,value[0])
                self.ymax = max(self.ymax,value[0])

            else:
              for iband in range(1,layer.bandCount()+1): # loop over the bands
                bandvalue=ident[layer.bandName(iband)]
                layernamewithband=layername
                if len(ident)>1:
                    layernamewithband+=' '+layer.bandName(iband)

                self.values.append((layernamewithband,bandvalue))

                if needextremum:
                    if layer.hasStatistics(i):
                        cstr=layer.bandStatistics(iband)
                        self.ymin=min(self.ymin,cstr.minimumValue)
                        self.ymax=max(self.ymax,cstr.maximumValue)
                    else:
                        self.ymin=min(self.ymin,layer.minimumValue(i))
                        self.ymax=max(self.ymax,layer.maximumValue(i))

        if self.checkBox.isChecked():
            #TODO don't plot if there is no data to plot...
          self.plot()
        else:
          self.printInTable()


    def calculateStatistics(self,layersWOStatistics):
        
        self.invalidatePlot()

        layerNames = QStringList()
        for layer in layersWOStatistics:
            if not layer.id() in self.layerMap:
                layerNames << layer.name()

        if ( len(layerNames) != 0 ):
            res = QMessageBox.warning( self, self.tr( 'Warning' ),
                                       self.tr( 'There are no statistics in the following rasters:\n%1\n\nCalculate?' ).arg(layerNames.join('\n')),
                                       QMessageBox.Yes | QMessageBox.No )
            if res != QMessageBox.Yes:
                #self.checkBox_2.setCheckState(Qt.Unchecked)  
                for layer in layersWOStatistics:
                    self.layerMap[layer.id()] = True
                return
        else:
            print('ERROR, no layers to get stats for')
        
        save_state=self.checkBox_2.isChecked()
        self.changeActive(Qt.Unchecked) # deactivate

        # calculate statistics
        for layer in layersWOStatistics:
            if not layer.id() in self.layerMap:
                self.layerMap[layer.id()] = True
                for i in range( 1,layer.bandCount()+1 ):
                    stat = layer.bandStatistics(i)

        if save_state:
            self.changeActive(Qt.Checked) # activate if necessary


    def printInTable(self):

        irow=0
        for row in self.values:
          layername,value=row
          if (self.tableWidget.item(irow,0)==None):
              # create the item
              self.tableWidget.setItem(irow,0,QTableWidgetItem())
              self.tableWidget.setItem(irow,1,QTableWidgetItem())

          self.tableWidget.item(irow,0).setText(layername)
          self.tableWidget.item(irow,1).setText(value)
          irow+=1


    def plot(self):

        numvalues=[]
        if ( (self.plotSelector.currentText()!='None') and (self.hasqwt or self.hasmpl) ):
            for row in self.values:
                layername,value=row
                try:
                    numvalues.append(float(value))
                except:
                    numvalues.append(0)

        if ( self.hasqwt and (self.plotSelector.currentText()=='Qwt') ):

            self.qwtPlot.setAxisMaxMinor(QwtPlot.xBottom,0)
            #self.qwtPlot.setAxisMaxMajor(QwtPlot.xBottom,0)
            self.qwtPlot.setAxisScale(QwtPlot.xBottom,1,len(self.values))
            self.qwtPlot.setAxisScale(QwtPlot.yLeft,self.ymin,self.ymax)
            
            self.curve.setData(range(1,len(numvalues)+1), numvalues)
            self.qwtPlot.replot()

        elif ( self.hasmpl and (self.plotSelector.currentText()=='matplotlib') ):

            if self.mplLine is None:
                self.mplPlt.clear()
                self.mplLine, = self.mplPlt.plot(range(1,len(numvalues)+1), numvalues, marker='o', color='k', mfc='b', mec='b', animated=True)
                self.mplPlt.set_xlim( (1-0.25,len(self.values)+0.25 ) )
                self.mplPlt.set_ylim( (self.ymin, self.ymax) )
                self.mplPlt.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
                self.mplPlt.yaxis.set_minor_locator(ticker.AutoMinorLocator())
                self.mplFig.canvas.draw()
                self.mplBackground = self.mplFig.canvas.copy_from_bbox(self.mplFig.bbox)
            else:
                # restore the clean slate background
                self.mplFig.canvas.restore_region(self.mplBackground)
                # update the data
                self.mplLine.set_ydata(numvalues)
                self.mplPlt.draw_artist(self.mplLine)
                # just redraw the axes rectangle
                self.mplFig.canvas.blit(self.mplFig.bbox)

        #try:
                #    attr = float(ident[j])
                #except:
                #    attr = 0
                #    print "Null cell value catched as zero!"  # For none values, profile height = 0. It's not elegant...

                    #nr = rastLayer.getRasterBandNumber(self.rastItems[field[1]][field[2]][0])

                    #print ident
            #for j in ident:
                #print j
                #if j.right(1) == str(nr):
       #attr = int(ident[j])
       #attr = float(ident[j])  ##### I MUST IMPLEMENT RASTER TYPE HANDLING!!!!
       #outFeat.addAttribute(i, QVariant(attr))


    def invalidatePlot(self):
        if self.mplLine is not None:
            del self.mplLine
            self.mplLine = None

    def resizeEvent(self, event):
        self.invalidatePlot()
