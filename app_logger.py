import sys
import time
import os
import logging
import logging.handlers
from message_out import MessageOut

# pylint: disable=too-many-instance-attributes
class AppLogger(object):
    logtype = {
        'SYSTEM' : 10,
        'USER' : 20,
        'GLOBAL' : 30
    }

    loglevel = {
        'DEBUG': 10,
        'INFO': 20,
        'WARN': 30,
        'ERROR': 40,
        'CRITICAL': 50,
    }

    def __init__(self, config, module):
        self.config = config
        self.module = module
        self.handlers = None
        self.log = None
        self.__setup_log(module)
        self.user_log_bytes = 0

        self.message_out = MessageOut(self.module, self.config)

        ## flush stdout to avoid out of order logging
        sys.stdout.flush()

    def debug(self, message, logtype=logtype['SYSTEM']):
        self.log.debug(message)
        if logtype == self.logtype['USER']:
            self.__publish_user_system_buffer(message, self.loglevel['DEBUG'])

        if logtype == self.logtype['SYSTEM']:
            self.__publish_system_buffer(message, self.loglevel['DEBUG'])

    def info(self, message, logtype=logtype['SYSTEM']):
        self.log.info(message)
        if logtype == self.logtype['USER']:
            self.__publish_user_system_buffer(message, self.loglevel['INFO'])

        if logtype == self.logtype['SYSTEM']:
            self.__publish_system_buffer(message, self.loglevel['INFO'])

    def warn(self, message, exc_info=None, logtype=logtype['SYSTEM']):
        self.log.warn(message, exc_info=exc_info)
        if logtype == self.logtype['USER']:
            self.__publish_user_system_buffer(message, self.loglevel['WARN'])

        if logtype == self.logtype['SYSTEM']:
            self.__publish_system_buffer(message, self.loglevel['WARN'])

    def error(self, message, exc_info=None, logtype=logtype['SYSTEM']):
        self.log.error(message, exc_info=exc_info)
        if logtype == self.logtype['USER']:
            self.__publish_user_system_buffer(message, self.loglevel['ERROR'])

        if logtype == self.logtype['SYSTEM']:
            self.__publish_system_buffer(message, self.loglevel['ERROR'])

    def critical(self, message, logtype=logtype['SYSTEM']):
        self.log.critical(message)
        if logtype == self.logtype['USER']:
            self.__publish_user_system_buffer(
                message, self.loglevel['CRITICAL'])

        if logtype == self.logtype['SYSTEM']:
            self.__publish_system_buffer(message, self.loglevel['CRITICAL'])

    def remove_handler(self, handler):
        self.log.removeHandler(handler)

    def __get_timestamp(self):
        # pylint: disable=no-self-use
        return int(time.time() * 1000000)

    def __publish_system_buffer(self, message, level):
        # pylint: disable=unused-argument
        if not self.config['SYSTEM_LOGGING_ENABLED']:
            ## DO NOT use self.log inside this block, causes recursion
            return

    def __publish_user_system_buffer(self, message, level):
        if not self.config['USER_SYSTEM_LOGGING_ENABLED']:
            return
        self.log.debug('Publishing logs: USER SYSTEM')
        system_output_line = {
            'consoleSequenceNumber' : self.__get_timestamp(),
            'output': message,
        }
        self.log.debug(system_output_line)

    def __setup_log(self, module_name):
        module_name = os.path.basename(module_name)
        module_name = module_name.split('.')[0]

        logger_name = self.module

        log_module_name = '{0} - {1}'.format(logger_name, module_name)
        self.log = logging.getLogger(log_module_name)
        self.log.setLevel(self.config['LOG_LEVEL'])

        self.log.propagate = True
        self.handlers = self.log.handlers

        # Silence urllib3 and requests
        if 'prod' in self.config['RUN_MODE'].lower():
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)

        self.log.debug('Log Config Setup successful: {0}'.format(module_name))
