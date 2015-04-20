# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.

import random
from functools import partial

from sgtk.platform.qt import QtCore, QtGui
from .ui import resources_rc

import tank
from tank import TankError


class TankNotificationsService(object):
    def __init__(self, app):
        """
        Construction
        """
        self._app = app
        self._widget = None
        self._running = False

    def is_running(self):
        """ Return True if the service is running """
        return self._running

    def start(self):
        print 'Notifications service starting ...'
        self._running = True
        self._widget = TankNotificationWidget(self._app)
        return self._running

    def stop(self):
        print 'Notifications service stopping ...'
        self._running = False
        # if self._widget is not None:
        #     self._widget.close()
        self._widget = None
        return self._running    

    def restart(self):
        if self._running:
            self.stop()
        self.start()
        return self._running


class ClickableLabel(QtGui.QLabel):
    """ A clickable QLabel """
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent=parent)

    def mouseReleaseEvent(self, event):
        self.clicked.emit()


class TankNotificationWidget(QtGui.QWidget):
    """ Widget displaying the notifications """
    def __init__(self, app):
        super(TankNotificationWidget, self).__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self._app = app
        self.create_layout()
        self.create_connections()
        # Show a test notification when starting
        self.show_test_notification()
        
    def create_layout(self):
        # Create the main layout
        self.layout = QtGui.QHBoxLayout()
        # Create the widgets
        self.logo = ClickableLabel()
        self.logo.setPixmap(QtGui.QPixmap(":/res/sg_logo.png"))
        self.logo.setToolTip('Click to open the related Shotgun page')
        self.message_label = QtGui.QLabel('')
        self.message_label.setToolTip('Right-click to close this notification')
        # Layout everything
        self.layout.addWidget(self.logo, 0)
        self.layout.addWidget(self.message_label, 1)
        # Set the layout as the widget layout
        self.setLayout(self.layout)

    def create_connections(self):
        self.logo.clicked.connect(self.open_shotgun)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.close()

    def show_message(self, message):
        self.message_label.setText(message)
        self.show()
        self.raise_()
        self.position_widget()
        self.animate_widget()

    def position_widget(self):
        """ Place the widget in the right corner of the parent application """
        desktop_rect = QtGui.QApplication.desktop().screenGeometry()        
        self._start_pos = QtCore.QPoint((desktop_rect.width() - 10), 30)
        self._end_pos = self._start_pos - QtCore.QPoint(self.width(), 0)
        self.move(self._start_pos)

    def animate_widget(self):
        anim = QtCore.QPropertyAnimation(self, "pos")
        anim.setDuration(500)
        anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim.setStartValue(self._start_pos)
        anim.setEndValue(self._end_pos)
        self._animgroup = QtCore.QParallelAnimationGroup()
        self._animgroup.addAnimation(anim)
        self._animgroup.start()

    def open_shotgun(self):
        url = self._app.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def show_test_notification(self):
        callback = partial(self.show_message, 'This is a notification test for %s' % self._app.context)
        self._timer = QtCore.QTimer.singleShot(random.randint(100, 5000), callback)
