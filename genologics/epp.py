"""Contains useful and reusable code for EPP scripts.

Classes, methods and exceptions.

Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2013 Johannes Alneberg
"""

import logging
import sys
import os
import pkg_resources
from pkg_resources import DistributionNotFound
from shutil import copy
from requests import HTTPError
from genologics.config import BASEURI
from genologics.entities import Artifact

def attach_file(src,resource):
    """Attach file at src to given resource

    Copies the file to the current directory, EPP node will upload this file
    automatically if the process output is properly set up"""
    original_name = os.path.basename(src)
    new_name = resource.id + '_' + original_name
    dir = os.getcwd()
    location = os.path.join(dir,new_name)
    copy(src,location)
    return location

class EmptyError(ValueError):
    "Raised if an iterator is unexpectedly empty."
    pass

class NotUniqueError(ValueError):
    "Raised if there are unexpectedly more than 1 item in an iterator"
    pass

def unique_check(l,msg):
    "Check that l is of length 1, otherwise raise error, with msg appended"
    if len(l)==0:
        raise EmptyError("No item found for {0}".format(msg))
    elif len(l)!=1:
        raise NotUniqueError("Multiple items found for {0}".format(msg))

    
class EppLogger(object):

    """Logger class that collect stdout, stderr and info."""

    PACKAGE = 'genologics'
    def __enter__(self):
        try:
            logging.info('Version: ' + pkg_resources.require(self.PACKAGE)[0].version)
        except DistributionNotFound as e:
            logging.error(e)
            logging.error('Make sure you have the {0} package installed'.format(self.PACKAGE))
            sys.exit(-1)
        return self

    def __exit__(self,exc_type,exc_val,exc_tb):
        # If no exception has occured in block, turn off logging.
        if not exc_type:
            logging.shutdown()
            sys.stderr = self.saved_stderr
            sys.stdout = self.saved_stdout
        # Do not repress possible exception
        return False

    def __init__(self,log_file,level=logging.INFO,lims=None,prepend=False):
        """ help string for __Init__ """
        self.lims = lims
        self.log_file = log_file
        self.level = level
        self.prepend = prepend
        if prepend:
            self.prepend_old_log()

        logging.basicConfig(
            level=self.level,
            format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
            filename=log_file,
            filemode='a'
            )

        stdout_logger = logging.getLogger('STDOUT')
        self.slo = self.StreamToLogger(stdout_logger, logging.INFO)
        self.saved_stdout = sys.stdout
        sys.stdout = self.slo

        stderr_logger = logging.getLogger('STDERR')
        self.sle = self.StreamToLogger(stderr_logger, logging.ERROR)
        self.saved_stderr = sys.stderr
        sys.stderr = self.sle

        self.logger = logging.getLogger()

    def prepend_old_log(self):
        """Prepend the old log stored locally to the new log. """
        # In try statement, catch non existent artifact error
        try:
            log_artifact = Artifact(self.lims,id=self.log_file)
            log_artifact.get()
            if log_artifact.files:
                log_path = log_artifact.files[0].content_location.split(BASEURI.split(':')[1])[1]
                dir = os.getcwd()
                destination = os.path.join(dir,self.log_file)
                copy(log_path,destination)
        except HTTPError: # Probably no artifact found, skip prepending
            logging.warning('No log file artifact found for id: {0}'.format(self.log_file))
        except IOError as e: # Probably some path was wrong in copy
            logging.error(('Log could not be prepended, make sure {0} and {1} '
                           'are proper paths.').format(log_path,self.log_file))
            raise e

    class StreamToLogger(object):
        """Fake file-like stream object that redirects writes to a logger instance.
        
        source: 
        http://www.electricmonk.nl/log/2011/08/14/
        redirect-stdout-and-stderr-to-a-logger-in-python/
        """
        def __init__(self, logger, log_level=logging.INFO):
            self.logger = logger
            self.log_level = log_level
            self.linebuf = ''

        def write(self, buf):
            for line in buf.rstrip().splitlines():
                self.logger.log(self.log_level, line.rstrip())

