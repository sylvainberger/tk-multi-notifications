# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

from sgtk.platform import Application

class MultiNotifications(Application):
    """
    Notification App displaying toast notifications in DCC
    """
    
    def init_app(self):
        """
        Called as the application is being initialized
        """
        
        # first, we use the special import_module command to access the app module
        # that resides inside the python folder in the app. This is where the actual UI
        # and business logic of the app is kept. By using the import_module command,
        # toolkit's code reload mechanism will work properly.
        tk_multi_notifications = self.import_module("tk_multi_notifications")
        # self.__notifications_handler = tk_multi_notifications.TankNotificationsHandler(self)

        # Initialize and Start the Notifications Service
        self._service = tk_multi_notifications.TankNotificationsService(self)
        
        # now register a *command*, which is normally a menu entry of some kind on a Shotgun
        # menu (but it depends on the engine). The engine will manage this command and 
        # whenever the user requests the command, it will call out to the callback.

        # first, set up our callback, calling out to a method inside the app module contained
        # in the python folder of the app
        menu_callback = lambda : tk_multi_notifications.dialog.show_dialog(self)

        # now register the command with the engine
        self.engine.register_command("Notifications", menu_callback)

    def destroy_app(self):
        """
        Called when the app is unloaded/destroyed
        """
        self.log_debug("Destroying tk-multi-notifications app")
        
        # Stop the service
        self._service.stop()
        self._service = None
        
    def service_running(self):
        return self._service.is_running()

    def start_service(self):
        return self._service.start()

    def stop_service(self):
        return self._service.stop()

    def restart_service(self):
        return self._service.restart()