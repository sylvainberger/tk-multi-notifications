# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import os
import sys
import threading

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.
from sgtk.platform.qt import QtCore, QtGui
# from .ui.dialog import Ui_Dialog

def show_dialog(app_instance):
    """
    Shows the main dialog window.
    """
    # in order to handle UIs seamlessly, each toolkit engine has methods for launching
    # different types of windows. By using these methods, your windows will be correctly
    # decorated and handled in a consistent fashion by the system.

    # we pass the dialog class to this method and leave the actual construction
    # to be carried out by toolkit.
    app_instance.engine.show_dialog("Notifications...", app_instance, AppDialog)


class AppDialog(QtGui.QWidget):
    """
    Main application dialog window
    """
    service_running = QtCore.Signal(int)
    START_TEXT = 'Start Notifications Service'
    STOP_TEXT = 'Stop Notifications Service'
    STATUS_STARTED = 'Started'
    STATUS_STOPPED = 'Stopped'

    def __init__(self):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)

        # now load in the UI that was created in the UI designer
        # self.ui = Ui_Dialog()
        # self.ui.setupUi(self)

        # most of the useful accessors are available through the Application class instance
        # it is often handy to keep a reference to this. You can get it via the following method:
        self._app = sgtk.platform.current_bundle()

        # via the self._app handle we can for example access:
        # - The engine, via self._app.engine
        # - A Shotgun API instance, via self._app.shotgun
        # - A tk API instance, via self._app.tk

        #  Create the layout
        self.create_layout()
        self.create_connections()
        self.update_status(self._app.service_running())

    def create_layout(self):
        # Create a main layout
        self.layout = QtGui.QVBoxLayout()
        # Create the widgets
        self.enable_notifications_checkbox = QtGui.QCheckBox('Enable Notifications')
        self.start_button = QtGui.QPushButton(self.START_TEXT)
        self.status_label = QtGui.QLabel('Status')
        self.status = QtGui.QLabel(self.STATUS_STOPPED)
        self.close_button = QtGui.QPushButton('Close')
        # Layout the status label and text
        self.status_layout = QtGui.QHBoxLayout()
        self.status_layout.addStretch(1)
        self.status_layout.addWidget(self.status_label, 0)
        self.status_layout.addWidget(self.status, 0)
        # Layout the close button
        self.footer_layout = QtGui.QHBoxLayout()
        self.footer_layout.addStretch(2)
        self.footer_layout.addWidget(self.close_button, 1)
        # Layout all the layout and widgets
        self.layout.addWidget(self.enable_notifications_checkbox, 0)
        self.layout.addWidget(self.start_button, 0)
        self.layout.addStretch(1)
        self.layout.addLayout(self.status_layout, 0)
        self.layout.addLayout(self.footer_layout, 0)
        # Set the main layout in the widget
        self.setLayout(self.layout)

    def create_connections(self):
        self.start_button.clicked.connect(self.start_or_stop_service)
        self.service_running.connect(self.update_status)
        self.close_button.clicked.connect(self.close)

    def start_or_stop_service(self):
        self.start_button.setEnabled(False)
        running = self._app.service_running()
        if self._app.service_running():
            self._app.stop_service()
        else:
            self._app.start_service()
        self.service_running.emit(self._app.service_running())
        self.start_button.setEnabled(True)

    def update_status(self, status):
        button_text = self.START_TEXT
        status_text = self.STATUS_STOPPED
        if status:
            button_text = self.STOP_TEXT
            status_text = self.STATUS_STARTED
        self.start_button.setText(button_text)
        self.status.setText(status_text)
