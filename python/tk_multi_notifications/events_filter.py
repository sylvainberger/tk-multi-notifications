""" 
This module contains class that handle querying
the shotgun event database and return an object
that will display a notification
""" 
import time

def log(msg):
    print time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) +": "+msg


class EventsFilter(object):
    """ Class used to """
    def __init__(self, shotgun_api, task=None, filter_classes=[]):
        super(EventsFilter, self).__init__()
        self.sg = shotgun_api
        self.task = task
        self.last_event_id = 0
        self._filters = []
        self.get_last_event_id()
        # init the class with the data we got in the arguments
        self.set_filters(filter_classes)

    def set_filters(self, filter_classes):
        """ Initialised the provided filters classes """
        for filter_class in filter_classes:
            self.add_filter(filter_class)

    def add_filter(self, filter_class):
        """ Instatiate the provide filter_class and store it in the filters list """
        self._filters.append(filter_class(self.sg, self.task, self.last_event_id))

    def filters(self):
        """ Return all the filters instances """
        return self._filters

    def get_last_event_id(self):
        """ Get the last event id from the event table """
        result = self.sg.find_one('EventLogEntry', filters=[], fields=['id'], order=[{'column':'id', 'direction':'desc'}])    
        self.last_event_id = result['id']

    def run(self):
        """ Run all the filters query and return all the filters containing valid events """
        log('Beginning processing starting at event #%d' % self.last_event_id)
        for _filter in self._filters:
            _filter.find()
        # Get the last event id and push it to the filter instances
        self.get_last_event_id()
        for _filter in self._filters:
            _filter.last_event_id = self.last_event_id


class EventFilterBase(object):
    """ Base class for filtering a shotgun event """
    event_type = ''

    def __init__(self, shotgun_api, task, last_event_id):
        super(EventFilterBase, self).__init__()
        self.sg = shotgun_api
        self.task = task
        self.last_event_id = last_event_id
        self.events = []

    def valid_events(self):
        return self._valid_events

    def _find(self):
        raise NotImplementedError()

    def _find_events(self):
        """ Find all event of the type stored in the class """
        events = self.sg.find('EventLogEntry',
                                filters=[
                                    ['event_type', 'is', self.event_type],
                                    ['id', 'greater_than', self.last_event_id],
                                ],
                                fields=['id', 'event_type', 'attribute_name', 'meta', 'entity'], 
                                order=[{'column':'created_at', 'direction':'asc'}], 
                                filter_operator='all')
        return events

    def find(self):
        self.events = self._find()
        return True if self.events else False

    def get_messages(self):
        """ Return a lis of notification message for every events found """
        messages = []
        for event in self.events:
            messages.append(self._message(event))
        return messages

    def _message(self, event):
        """ build the message list for every event """
        raise NotImplementedError()


class TaskStatusChangedFilter(EventFilterBase):
    """ Filter current task status changed """
    event_type = 'Shotgun_Task_Change'

    def __init__(self, *args, **kwargs):
        super(TaskStatusChangedFilter, self).__init__(*args, **kwargs)
        self.statuses = None
        
    def get_statuses(self):
        """ Get all the statuses from the database """ 
        if self.statuses is None:
            self.statuses = {}
            for status in self.sg.find('Status', filters=[], fields=['name', 'code']):
                self.statuses[status['code']] = status['name']

    def get_status_from_code(self, code):
        """ Given a status code, return the name of that status """
        self.get_statuses()
        return self.statuses.get(code, '')

    def _find(self):
        """ Find all the valid events """
        # Get all thes statuses 
        self.get_statuses()
        # Store the event and the status
        events_data = []
        for event in self._find_events():
            if event['attribute_name'] != 'sg_status_list':
                continue
            # Get the status
            status = self.get_status_from_code(event['meta']['new_value'])
            events_data.append((event, status))
        return events_data
        
    def _message(self, event_data):
        """ build the message for the provided event """
        # extract the event and the status from the tuple
        event, status = event_data
        message = 'Status of task %s %s changed to %s' % (self.task['entity']['name'], event['entity']['name'], status)
        return message
        

class NewPublishFilter(EventFilterBase):
    """ Filter new publishes linked to the current task """
    event_type = 'Shotgun_PublishedFile_New'

    def __init__(self, *args, **kwargs):
        super(NewPublishFilter, self).__init__(*args, **kwargs)
        self.statuses = None

    def _find(self):
        """ Find all the valid events """
        events_data = []
        for event in self._find_events():
            # Find the matching publish document
            publish = self.sg.find_one("PublishedFile",
                                    filters=[['id', 'is', event['entity']['id']]],
                                    fields=['id','published_file_type', 'code', 'entity'], 
                                    filter_operator='all',                                
                                 )
            # Only keep the publish if it is linked to the task or the task entity 
            if publish['entity'] and publish['entity']['id'] == self.task['entity']['id']:
                events_data.append((event, publish))
        return events_data

    def _message(self, event_data):
        """ build the message for the provided event """
        event, publish = event_data
        publish_type = publish['published_file_type']
        entity_name = publish['entity']['name']
        if publish_type is not None:
            message = 'A new %s "%s" was published for entity %s' % (publish_type['name'], publish['code'], entity_name)    
        else:
            message = 'A new element "%s" was published for entity %s' % (publish['code'], entity_name)
        return message
       

class NewNoteFilter(EventFilterBase):
    """ Filter new notes events linked to the current task """
    event_type = 'Shotgun_Note_New'

    def __init__(self, *args, **kwargs):
        super(NewNoteFilter, self).__init__(*args, **kwargs)
        self.statuses = None

    def _find(self):
        """ Find all the valid events """
        events_data = []
        for event in self._find_events():
            note = self.sg.find_one('Note', 
                                        filters=[
                                            ['id', 'is', event['entity']['id']],       
                                            ['tasks', 'is', { 'type': 'Task', 'id': self.task['id'] }],
                                        ],
                                        fields=['id', 'subject', 'content', 'user', 'tasks', 'note_links']
                                    )
            if not note:
                continue
            events_data.append((event, note))
        return events_data

    def _message(self, event_data):
        """ build the message for the provided event """
        event, note = event_data
        user = note['user']['name']
        note_link = note['note_links']
        if isinstance(note_link, list):
            note_link = note_link[-1]['name']
        message = 'A new note by %s was added on %s' % (user, note_link)
        return message
        



  # def find_note_on_task(task_id):
  #   notes = sg.find("Note", 
  #                       filters=[['tasks', 'is', {'type': 'Task', 'id': task_id}]],
  #                       fields=['id', 'subject', 'content', 'user', 'tasks', 'note_links'])      

if __name__ == '__main__':
    from tests import test_events_filters
    test_events_filters.test()

            
