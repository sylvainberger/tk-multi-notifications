import os
import sys

# add path to be able to import the modules we need for the tests
paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'python-api')),
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
]
for path in paths:
    if not path in sys.path:
        sys.path.insert(0, path)

from shotgun_api3 import Shotgun
from events_filter import EventsFilter
from events_filter import TaskStatusChangedFilter
from events_filter import NewPublishFilter
from events_filter import NewNoteFilter

SERVER_PATH = 'https://sberger.shotgunstudio.com' # make sure to change this to https if your studio uses it.
SCRIPT_USER = 'Sandbox'
SCRIPT_KEY = '479f0f7fe7f3a2e935ec99d61b760139f73890bd0e8d09edb417eaac65990061'

sg = Shotgun(SERVER_PATH, SCRIPT_USER, SCRIPT_KEY)


def test():
    task_id = 560
    task = sg.find_one("Task", filters=[['id', 'is', task_id]], fields=['id', 'entity'])

    event_filter = EventsFilter(sg, task)
    event_filter.last_event_id = 239000
    event_filter.add_filter(TaskStatusChangedFilter)
    event_filter.add_filter(NewPublishFilter)
    event_filter.add_filter(NewNoteFilter)
    event_filter.run()
    print '-' * 100
    for f in event_filter.filters():
        for n in f.get_notifications():
            print '--'
            print n.get_message()
            print n.get_url()

if __name__ == '__main__':
    test()
