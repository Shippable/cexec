import json
import os
from base import Base
from script_runner import ScriptRunner

class Execute(Base):
    def __init__(self):
        Base.__init__(self, __name__)
        self.user_headers = None
        self.publish_queue = None
        self.script_runner = None

    def __validate_message(self, raw_message):
        self.log.debug('Validating message')
        error_message = ''
        error_occurred = False
        try:
            self.parsed_message = json.loads(raw_message)
            steps = self.parsed_message.get('steps')
            if not steps:
                error_message = 'No "steps" property present'
                raise Exception(error_message)

            return steps
        except ValueError as verr:
            error_message = 'Invalid message received: ' \
                            'Error : {0} : {1}'.format(str(verr), raw_message)
            error_occurred = True
        except Exception as err:
            error_message = 'Invalid message received: ' \
                            'Error : {0} : {1}'.format(str(err), raw_message)
            error_occurred = True
        finally:
            if error_occurred:
                self.log.error(error_message, self.log.logtype['USER'])
                raise Exception(error_message)

    def run(self):
        self.log.debug('Inside Execute ')
