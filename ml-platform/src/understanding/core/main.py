#!/usr/bin/env python

import os
from kink import di
from logging import Logger
from data_understander import DataUnderstander
from sagemaker_repository_interface import SagemakerLocalRepository
from logger import LoggerFactory

LOGLEVEL = os.getenv('LOGLEVEL')
MODE = os.getenv('MODE')

di[Logger] = LoggerFactory.create_logger(LOGLEVEL or "INFO")
di["SagemakerLocalInputPath"] = '/opt/ml/processing/input/data'
di["SagemakerLocalOutputPath"] = '/opt/ml/processing/output/data'

di[SagemakerLocalRepository] = SagemakerLocalRepository(
    di["SagemakerLocalInputPath"],
    di["SagemakerLocalOutputPath"],
    MODE == "DEVELOPMENT"
)

def main():
    try:
        usecase = DataUnderstander()
        usecase.understand()
    except Exception as e:
        print(e)
        raise e


if __name__ == "__main__":
    main()