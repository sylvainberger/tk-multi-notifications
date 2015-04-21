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
        self._widget = TankNotificationWidget(self._app)

    def is_running(self):
        """ Return True if the service is running """
        if self._widget is None:
            return False
        return self._widget._active

    def start(self):
        print 'Notifications service starting ...'
        self._running = True
        self._widget.start()
        return self._widget._active

    def stop(self):
        print 'Notifications service stopping ...'
        self._running = False
        self._widget.stop()
        return self._widget._active    

    def restart(self):
        if self.is_running():
            self.stop()
        self.start()
        return self.is_running()


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
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self._timer = None
        self._timer_delay = 5000
        self._active = False
        self._app = app
        self.create_layout()
        self.create_connections()
        # Start a timer that will check for new notifications
        # when the timer runs out
        self.create_timer()
        
    def create_layout(self):
        """ Create the main layout for this widget """
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
        """ Create the connections of this widget """
        self.logo.clicked.connect(self.open_shotgun)

    def start(self):
        """ 
        Check for notification, this will start an infinite loop
        of notification check > start a timer > notification check > etc
        """
        self._active = True
        self.check_for_notifications()

    def stop(self):
        """ Set the self._active member value False, 
        After the timer start is checking of this valueif it is off
        the timer > check loop will stop
        """
        self._active = False

    def create_timer(self):
        """ Create a timer that check for new notifications when it runs out """
        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.check_for_notifications)

    def start_timer(self, delay):
        """ Start the timer with the provided delay """
        if self._active:
            self._timer.start(delay)

    def check_for_notifications(self):
        """ Launch a thread that will query Shotgun to get notifications and display them """
        if not self._active:
            return
        thread = NotificationThread(self._app.context, parent=self)
        # This connection will show a notification message if a notification
        # is found by the thread
        thread.notification_message.connect(self.show_message)
        # When the thread is finished, start a new timer that will 
        # execute this method again at the end of the timer
        thread.finished.connect(partial(self.start_timer, self._timer_delay))
        # Start the thread
        thread.start()

    def mouseReleaseEvent(self, event):
        """ Close the notification message on right click """
        if event.button() == QtCore.Qt.RightButton:
            self.close()

    def show_message(self, message):
        """ Show a notification message """
        self.message_label.setText(message)
        self.show()
        self.raise_()
        self.position_widget()
        self.animate_widget()

    def position_widget(self):
        """ 
        Place the widget just ouside the right corner of desktop 
        Define the final position, in the top right corner of the desktop
        """
        desktop_rect = QtGui.QApplication.desktop().screenGeometry()        
        self._start_pos = QtCore.QPoint((desktop_rect.width() - 10), 30)
        self._end_pos = self._start_pos - QtCore.QPoint(self.width(), 0)
        self.move(self._start_pos)

    def animate_widget(self):
        """ Run the animation that will move the widget in the view """
        anim = QtCore.QPropertyAnimation(self, "pos")
        anim.setDuration(500)
        anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim.setStartValue(self._start_pos)
        anim.setEndValue(self._end_pos)
        self._animgroup = QtCore.QParallelAnimationGroup()
        self._animgroup.addAnimation(anim)
        self._animgroup.start()

    def open_shotgun(self):
        """ Open the shotgun website at the current context """
        url = self._app.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))


class NotificationThread(QtCore.QThread):
    """  Main thread loop querying Shotgun to get new data to notify"""
    notification_message = QtCore.Signal(unicode)

    def __init__(self, context, parent=None):
        super(NotificationThread, self).__init__(parent)
        self._context = context

    def start(self):
        print 'Starting thread...'
        super(NotificationThread, self).start()
        self.setPriority(QtCore.QThread.LowPriority)

    def run(self):
        # Check if there is a new event in Shotgun

        # Fake a message for a test
        messages = ['Random message 1 for context %s' % self._context,
                    'Random message 2 for context %s' % self._context,
                    'Random message 3 for context %s' % self._context,
                    'Random message 4 for context %s' % self._context,
                    ]
        self.notification_message.emit(messages[random.randint(0, len(messages) - 1)])
