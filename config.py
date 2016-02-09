import os
import logging
from urlparse import urlparse

class Config(dict):
    """
    Global config. CEXEC does not boot up unless all variables defined here are
    initialized
    """
    def __init__(self):
        self['HOME'] = os.getenv('HOME', '/root')

        self['USER_BUFFER_TIMEOUT'] = 2
        self['MAX_USER_LOG_SIZE'] = 12 * 1024 * 1024
        self['CONSOLE_BUFFER_LENGTH'] = 20
        self['CONSOLE_FLUSH_INTERVAL'] = 3

        self['RUN_MODE'] = os.getenv('RUN_MODE', 'PROD')
        if 'prod' in self['RUN_MODE'].lower():
            self['LOG_LEVEL'] = 'INFO'
        elif 'beta' in self['RUN_MODE'].lower():
            self['LOG_LEVEL'] = 'INFO'
        else:
            self['LOG_LEVEL'] = 'DEBUG'

        self['SHIPPABLE_API_URL'] = os.getenv('SHIPPABLE_API_URL', '')
        self['SHIPPABLE_VORTEX_URL'] = "{0}/vortex".format(self['SHIPPABLE_API_URL'])
        self['SHIPPABLE_API_RETRY_INTERVAL'] = os.getenv('SHIPPABLE_API_RETRY_INTERVAL', '')

        self['SYSTEM_LOGGING_ENABLED'] = False
        self['USER_SYSTEM_LOGGING_ENABLED'] = True

        self['MESSAGE_DIR'] = os.getenv('MESSAGE_DIR', '/tmp/cexec')
        self['MESSAGE_JSON_NAME'] = os.getenv('MESSAGE_JSON_NAME', 'message.json')
        self['WHO'] = os.getenv('WHO', 'cexec')
        self['SSH_DIR'] = os.getenv('SSH_DIR', '/tmp/ssh')
        self['ARTIFACTS_DIR'] = os.getenv('ARTIFACTS_DIR', '/shippableci')

        for k, v in self.iteritems():
            if v == '':
                print('{0} has no value. Make sure the container environment has a '
                               'variable {0} with a valid value'.format(k))
                raise Exception('{0} has no value. Make sure the container environment has a '
                               'variable {0} with a valid value'.format(k))

        # Convert SHIPPABLE_API_RETRY_INTERVAL to an int
        self['SHIPPABLE_API_RETRY_INTERVAL'] = int(
            self['SHIPPABLE_API_RETRY_INTERVAL'])

    def __str__(self):
        for k, v in self.iteritems():
            print('{0} - {1}'.format(k, v))
        return ''
