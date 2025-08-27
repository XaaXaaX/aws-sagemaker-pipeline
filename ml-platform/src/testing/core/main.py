#!/usr/bin/env python

import os
from kink import di
from logging import Logger
from model_validator import ModelValidation
from fs_repository_interface import FileSystemRepository
from logger import LoggerFactory

LOGLEVEL = os.getenv('LOGLEVEL')
MODE = os.getenv('MODE')

inputPath = '../../../data' #'/opt/ml/processing/input/data'
outputPath = '../../../data' #'/opt/ml/processing/output/data'

di[Logger] = LoggerFactory.create_logger(LOGLEVEL or "INFO")
di[FileSystemRepository] = FileSystemRepository(
    inputPath,
    outputPath,
    MODE == "DEVELOPMENT"
)

def main():
    validator = ModelValidation()
    validator.validate()

if __name__ == "__main__":
    main()
