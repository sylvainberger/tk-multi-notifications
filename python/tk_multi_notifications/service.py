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

import time
import random
from functools import partial

from sgtk.platform.qt import QtCore, QtGui
from events_filter import EventsFilter
from events_filter import TaskStatusChangedFilter
from events_filter import NewPublishFilter
from events_filter import NewNoteFilter
from .ui import resources_rc

import tank
from tank import TankError


def log(msg):
    print time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) +": "+msg


class TankNotificationsService(object):
    def __init__(self, app):
        """
        Construction
        """
        self._app = app
        # Get the task daa required
        task = self._find_task(self._app.context.task['id'])
        # Initialize the event filter instance
        self._event_filter = EventsFilter(self._app.shotgun, task)
        self._event_filter.add_filter(TaskStatusChangedFilter)
        self._event_filter.add_filter(NewPublishFilter)
        self._event_filter.add_filter(NewNoteFilter)
        # Initialize the notification widget
        self._widget = TankNotificationWidget(self, self._event_filter)

    def _find_task(self, task_id):
        """ Return the task data of of the provided task id """
        return self._app.shotgun.find_one("Task", filters=[['id', 'is', task_id]], fields=['id', 'entity'])

    def is_running(self):
        """ Return True if the service is running """
        if self._widget is None:
            return False
        return self._widget._active

    def start(self):
        log('Notifications service starting ...')
        # Only start the service if there is a task in the current context
        if self._app.context.task is None:
            log('The context is not valid. Notifications service cannot start.')
            return False
        self._widget.start()
        return self._widget._active

    def stop(self):
        log('Notifications service stopping ...')
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
    def __init__(self, parent, event_filter):
        super(TankNotificationWidget, self).__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self._timer = None
        self._timer_delay = 5000
        self._active = False
        self.parent = parent
        self._url = self.get_default_url()
        self._event_filter = event_filter
        self._message_displaying = False
        self.create_layout()
        self.create_connections()
        # Start a timer that will check for new notifications when the timer runs out
        self.create_timer()

    @property
    def _app(self):
        return self.parent._app

    @property
    def context(self):
        return self._app.context

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
        if self._message_displaying:
            print 'Message is being displayed. Waiting for the message to close.'
        if self._active and not self._message_displaying:
            print 'Starting timer....'
            self._timer.start(delay)

    def check_for_notifications(self):
        """ Launch a thread that will query Shotgun to get notifications and display them """
        if not self._active:
            return
        thread = NotificationThread(self)
        # This connection will show a notification message if a notification
        # is found by the thread
        thread.notification_url.connect(self.set_url)
        thread.notification_message.connect(self.show_message)
        # When the thread is finished, start a new timer that will
        # execute this method again at the end of the timer
        thread.finished.connect(partial(self.start_timer, self._timer_delay))
        # Start the thread
        thread.start()

    @QtCore.Slot(unicode)
    def show_message(self, message):
        """ Show a notification message """
        self.message_label.setText(message)
        self._message_displaying = True
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

    def get_default_url(self):
        return self.context.shotgun_url

    @QtCore.Slot(unicode)
    def set_url(self, url):
        """ Set the current url to the provided url """
        if url:
            self._url = url
        else:
            self._url = self.get_default_url()
        # entity page example
        # https://sberger.shotgunstudio.com/page/email_link?entity_id=6003&entity_type=Version
        # Task page example
        # https://sberger.shotgunstudio.com/page/email_link?entity_id=560&entity_type=Task
        # Shot page example
        # https://sberger.shotgunstudio.com/page/email_link?entity_id=860&entity_type=Shot
        # Note link example
        # https://sberger.shotgunstudio.com/page/email_link?entity_id=6021&entity_type=Note

    def open_shotgun(self):
        """ Open the shotgun website at the current context """
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self._url))

    def mouseReleaseEvent(self, event):
        """ Close the notification message on right click """
        if event.button() == QtCore.Qt.RightButton:
            self.close()
            self._message_displaying = False
            # Start a new timer when the message is closed
            self.start_timer(1000)


class NotificationThread(QtCore.QThread):
    """  Main thread loop querying Shotgun to get new data to notify"""
    notification_message = QtCore.Signal(unicode)
    notification_url = QtCore.Signal(unicode)

    def __init__(self, parent):
        super(NotificationThread, self).__init__(parent)
        self.parent = parent

    def start(self):
        log('Starting thread...')
        super(NotificationThread, self).start()
        self.setPriority(QtCore.QThread.LowPriority)

    def run(self):
        # Run the event filter
        self.parent._event_filter.run()
        # loop all filters results
        notifications = []
        for _filter in self.parent._event_filter.filters():
            for notification in _filter.get_notifications():
                notifications.append(notification)

        # Return if we got nothing
        if not notifications:
            return

        # Show the message or the number of notification since the last update
        if len(notifications) == 1:
            msg = notifications[0].get_message()
            url = notifications[0].get_url()
        else:
            msg = '%d new activity in task %s' % (len(notifications), self.parent.context.task['name'])
            url = ''
        # Emit the url first because the message emit will show the notification widget
        self.notification_url.emit(url)
        self.notification_message.emit(msg)
