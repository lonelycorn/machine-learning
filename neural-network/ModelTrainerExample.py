#!/usr/bin/env python3
import argparse
import json
import logging
import numpy
import sys

from ModelTrainerBase import ModelTrainerBase

from MachineLearningUtils import (
    Constants,
    Utils,
)

class ModelTrainerExample(ModelTrainerBase):

    def initDataset(self, dataset: str):
        '''
        interface
        '''
        if dataset == Constants.DATASET_MNIST:
            self.mTrainInput = numpy.fromfile(Constants.FILE_TRAIN_INPUT, dtype=numpy.uint8)
            self.mTrainOutput = numpy.fromfile(Constants.FILE_TRAIN_LABELS, dtype=numpy.uint8)
            self.mTestInput = numpy.fromfile(Constants.FILE_TEST_INPUT, dtype=numpy.uint8)
            self.mTestOutput = numpy.fromfile(Constants.FILE_TEST_LABELS, dtype=numpy.uint8)

            self.mNumTrainSamples = Utils.bytesToInt(self.mTrainInput, 0)
            self.mDimInput = Utils.bytesToInt(self.mTrainInput, 4)
            assert(self.mNumTrainSamples == Utils.bytesToInt(self.mTrainOutput, 0))
            assert(self.mDimInput == Utils.bytesToInt(self.mTestInput, 4))
            self.mNumTestSamples = Utils.bytesToInt(self.mTestInput, 0)
            assert(self.mNumTestSamples == Utils.bytesToInt(self.mTestOutput, 0))
            self.mDimOutput = 10

            self.mTrainInput = self.mTrainInput[8:].reshape(self.mNumTrainSamples, self.mDimInput)
            self.mTrainInput = self.mTrainInput / 255.0
            self.mTestInput = self.mTestInput[8:].reshape(self.mNumTestSamples, self.mDimInput)
            self.mTestInput = self.mTestInput / 255.0

            data = self.mTrainOutput[4:]
            self.mTrainOutput = numpy.zeros((self.mNumTrainSamples, self.mDimOutput))
            for (sample, d) in zip(self.mTrainOutput, data):
                sample[d] = 1

            data = self.mTestOutput[4:]
            self.mTestOutput = numpy.zeros((self.mNumTestSamples, self.mDimOutput))
            for (sample, d) in zip(self.mTestOutput, data):
                sample[d] = 1
            '''
            for index in range(0, self.mNumTestSamples):
                self.mTestOutput[data[index], index] = 1
            '''
            self.mTrainInput.astype('float128')
            self.mTestInput.astype('float128')
            self.mTrainOutput.astype('float128')
            self.mTestOutput.astype('float128')

        else:
            raise ValueError(f"Could not init Dataset {dataset}")

    def parseConfig(self, config: str):
        '''
        override
        '''
        print(f"ModelTrainerExample is parsing {config}")

    def trainModel(self):
        '''
        override
        '''
        self.mTestMatrix = numpy.random.normal(0.0, 1.0, (self.mDimOutput, self.mDimInput))

    def getResults(self):
        '''
        override
        '''
        output = numpy.dot(self.mTestMatrix, self.mTrainInput)
        trainAccuracy = Utils.compare(Utils.getPredictions(output), self.mTrainOutput)

        output = numpy.dot(self.mTestMatrix, self.mTestInput)
        testAccuracy = Utils.compare(Utils.getPredictions(output), self.mTestOutput)

        return trainAccuracy, testAccuracy
