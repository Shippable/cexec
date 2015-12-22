import sys
import uuid
import time
import datetime
import os
import threading
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
        self.__setup_log(module)
        self.user_log_bytes = 0
        self.header_params = None

        self.message_out = MessageOut(self.module, self.config)

        self.console_buffer = []
        self.console_buffer_lock = threading.Lock()

        ## flush stdout to avoid out of order logging
        sys.stdout.flush()

    def init_user_logger(self, header_params):
        ## user params get published as-is in the message
        ## user params should be key-value pairs
        if type(header_params) is dict:
            self.header_params = header_params

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

    def reset_console_buffer(self):
        del self.console_buffer
        self.console_buffer = []

    def append_console_buffer(self, console_out):
        with self.console_buffer_lock:
            self.console_buffer.append(console_out)

        if len(self.console_buffer) > self.config['CONSOLE_BUFFER_LENGTH']:
            self.flush_console_buffer()

    def __publish_user_system_buffer(self, message, level):
        if not self.config['USER_SYSTEM_LOGGING_ENABLED']:
            return
        self.log.debug('Publishing logs: USER SYSTEM')
        system_output_line = {
            'consoleSequenceNumber' : self.__get_timestamp(),
            'output': message,
        }
        self.log.debug(system_output_line)
        user_system_message = {
            'headers' : {
                'type' : self.logtype['GLOBAL'],
                'level' : level,
                'step' : self.config['STEP_NAME'],
                'messageDate': datetime.datetime.utcnow().isoformat(),
            },
            'updateSequenceNumber': self.__get_timestamp(),
            'consoleLogBytes': sys.getsizeof(message),
            'module': self.module,
            'timestamp': self.__get_timestamp(),
            'console': [system_output_line],
        }

        for header_param in self.header_params:
            user_system_message['headers'][header_param] = \
                self.header_params[header_param]

    def flush_console_buffer(self):
        self.log.info('Flushing console buffer to vortex')
        if len(self.console_buffer) == 0:
            self.log.debug('No console output to flush')
        else:
            with self.console_buffer_lock:
                self.log.debug('Flushing {0} console logs'.format(
                    len(self.console_buffer)))
                console_message = {
                    'headers' : {
                        'timestamp': self.__get_timestamp(),
                    },
                    'updateSequenceNumber': self.__get_timestamp(),
                    'consoleLogBytes': self.user_log_bytes,
                    'console' : self.console_buffer,
                }

                for header_param in self.header_params:
                    console_message['headers'][header_param] = \
                        self.header_params[header_param]

                self.message_out.console(console_message)

                del self.console_buffer
                self.console_buffer = []

    def __setup_log(self, module_name):
        module_name = os.path.basename(module_name)
        module_name = module_name.split('.')[0]

        project_root = os.path.split(
            os.path.normpath(os.path.abspath(__file__)))[0]
        log_dir = (project_root + '/logs').replace('//', '/')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        logger_name = self.module
        log_file = self.__get_log_file_name(logger_name, 'log', log_dir)
        with open(log_file, 'a'):
            os.utime(log_file, None)

        log_module_name = '{0} - {1}'.format(logger_name, module_name)
        self.log = logging.getLogger(log_module_name)
        self.log.setLevel(self.config['LOG_LEVEL'])

        self.log.propagate = True
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10000000, backupCount=2)
        handler.setLevel(self.config['LOG_LEVEL'])
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)
        self.handlers = self.log.handlers
        self.log.debug('Log Config Setup successful: {0}'.format(module_name))

    def __get_log_file_name(self, name, ext, folder):
        new_name = '{0}/{1}.{2}'.format(folder, name, ext)
        return new_name

    def log_command_op(self, output):
        console_out = {
            'consoleId': str(uuid.uuid4()),
            'parentConsoleId': '',
            'type': 'msg',
            'message' : output,
            'msgTimestamp': self.__get_timestamp(),
            'completed' : True
        }
        self.console_buffer.append(console_out)

    def log_command_err(self, err):
        console_out = {
            'consoleId': str(uuid.uuid4()),
            'parentConsoleId': '',
            'type': 'msg',
            'message' : err,
            'msgTimestamp': self.__get_timestamp(),
            'completed' : False
        }
        self.console_buffer.append(console_out)
