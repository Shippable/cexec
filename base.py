import os
import subprocess
from config import Config
from app_logger import AppLogger

class Base(object):
    STATUS = {
        'WAITING': 0,
        'QUEUED': 10,
        'PROCESSING': 20,
        'SUCCESS': 30,
        'SKIPPED': 40,
        'UNSTABLE': 50,
        'TIMEOUT': 60,
        'CANCELLED': 70,
        'FAILED': 80
    }

    def __init__(self, module_name):
        self.module = module_name
        self.config = Config()
        self.log = AppLogger(self.config, self.module)
