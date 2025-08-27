#!/usr/bin/env python

import os
from kink import di
from logging import Logger
from data_preprocessing import DataPreProcessing
from fs_repository_interface import FileSystemRepository
from logger import LoggerFactory

LOGLEVEL = os.getenv('LOGLEVEL')
MODE = os.getenv('MODE')

di[Logger] = LoggerFactory.create_logger(LOGLEVEL or "INFO")
inputPath = '/opt/ml/processing/input'
outputPath = '/opt/ml/processing/output'
inputPath = '../../../data/input'
outputPath = '../../../data'

di[FileSystemRepository] = FileSystemRepository(
    inputPath,
    outputPath,
    MODE == 'DEVELOPMENT'
)

def main():
    try:
        usecase = DataPreProcessing()
        usecase.prepare()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()