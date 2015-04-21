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
        self._widget = TankNotificationWidget(self._app)

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
    def __init__(self, app):
        super(TankNotificationWidget, self).__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self._timer = None
        self._timer_delay = 5000
        self._active = False
        self._app = app
        self._message_displaying = False
        self._last_event_id = 0
        self.create_layout()
        self.create_connections()
        # Start a timer that will check for new notifications when the timer runs out
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
        if self._message_displaying:
            print 'Message is being displayed. Waiting for the message to close.'
        if self._active and not self._message_displaying:
            print 'Starting timer....'
            self._timer.start(delay)

    def check_for_notifications(self):
        """ Launch a thread that will query Shotgun to get notifications and display them """
        if not self._active:
            return
        thread = NotificationThread(self, self._app.context, self._last_event_id)
        # This connection will show a notification message if a notification
        # is found by the thread
        thread.notification_message.connect(self.show_message)
        # connect the last_event signal to be able to store the last event parsed
        thread.last_event.connect(self.store_last_event)
        # When the thread is finished, start a new timer that will 
        # execute this method again at the end of the timer
        thread.finished.connect(partial(self.start_timer, self._timer_delay))
        # Start the thread
        thread.start()

    @QtCore.Slot(int)
    def store_last_event(self, event_id):
        self._last_event_id = event_id

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

    def open_shotgun(self):
        """ Open the shotgun website at the current context """
        url = self._app.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

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
    last_event = QtCore.Signal(int)

    def __init__(self, parent, context, last_event_id):
        super(NotificationThread, self).__init__(parent)
        self.sg = parent._app.shotgun
        self.context = context
        self.last_event_id = last_event_id

    def start(self):
        log('Starting thread...')
        super(NotificationThread, self).start()
        self.setPriority(QtCore.QThread.LowPriority)

    def run(self):
        # Check if there is a new event in Shotgun
        events = self.find_events()
        # Emit the last event so we can store it in the parent and push it back again in the next thread
        self.last_event.emit(self.last_event_id)
        if not events:
            return
        # Emit the notification message
        if len(events) == 1:
            e = events[0]
            if e['event_type'] == 'Shotgun_Task_Change':
                message = 'Status of task %s changed to %s' % (e['entity']['name'], e['meta']['new_value'])
            else:
                message = 'New activity in task %s' % e['entity']['name']
        else:
            message = '%d new activity in task %s' % (len(events), self.context.task['name'])
        self.notification_message.emit(message)

    def find_events(self):
        """ Function returning all the event for the current task_id since the last check """
        valid_events = ['Shotgun_Note_New', 'Shotgun_Task_Change']
        # ---------------------------------------------------------------------------------------------
        # get the id of the latest EventLogEntry
        # ---------------------------------------------------------------------------------------------
        if not self.last_event_id:
            result = self.sg.find_one("EventLogEntry",filters=[], fields=['id'], order=[{'column':'created_at','direction':'desc'}])    
            self.last_event_id = result['id']
        log('beginning processing starting at event #%d' % self.last_event_id)

        # ---------------------------------------------------------------------------------------------
        # find all Events since the last check
        # ---------------------------------------------------------------------------------------------
        events = []
        task_id = self.context.task['id']
        if not task_id:
            return events

        # Find all the lastest event for the task id
        for event in self.sg.find("EventLogEntry",filters=[['id', 'greater_than', self.last_event_id], ['entity', 'is', { "type": "Task", "id": task_id }]], 
                                fields=['id','event_type','attribute_name','meta','entity'], 
                                order=[{'column':'created_at','direction':'asc'}], filter_operator='all'):
            log('processing event id %d' % event['id'])

            # Ignore invalid event types
            if event['event_type'] in valid_events:
                print event
                events.append(event)
        if events:
            self.last_event_id = events[-1]['id']
        return events