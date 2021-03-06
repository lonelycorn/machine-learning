import json
import numpy as np
import time

import ActivationFunction
import CostFunction
import ModelTrainerBase
from MachineLearningUtils import Utils


class Node:
    """
    Each node represents a neuron / perceptron
    """
    def __init__(self, id, activationFunction, tag=None):
        self.mId = id
        if (tag is None):
            self.mTag = "hidden"
        else:
            self.mTag = tag

        # neuron definition
        self.mNodeIdToInputIdx = {}
        self.mInputs = []
        self.mOutputs = []
        self.mActivationFunction = activationFunction

        # neuron parameters
        self.mInputWeights = []
        self.mInputBias = 0.0

        # latest input activations to the neuron
        #       [ ... a_j ...]
        self.mLatestInputs = []
        # latest output activation of the neuron
        #       z = sum( w_j * a_j) + b
        #       a = f(z) where f() is the activation function
        self.mLatestActivation = 0
        #       d_a_over_d_z
        self.mLatestActivationDerivative = 0
        # latest partial derivative of the cost to z
        #       par_C_over_par_z
        self.mLatestCostPartialDerivative = 0

        # for (stochastic) gradient descent
        self.mDeltaInputWeights = []
        self.mDeltaInputBias = 0.0
        self.mSampleCount = 0


    @property
    def id(self):
        return self.mId


    @property
    def tag(self):
        return self.mTag


    def getLatestActivation(self):
        return self.mLatestActivation


    def getLatestCostPartialDerivative(self):
        return self.mLatestCostPartialDerivative


    def getInputWeight(self, neuronId):
        return self.mInputWeights[self.mNodeIdToInputIdx[neuronId]]


    def registerInput(self, n):
        """
        use during configuration
        """
        if (n not in self.mInputs):
            self.mNodeIdToInputIdx[n.id] = len(self.mInputs)
            self.mInputs.append(n)


    def registerOutput(self, n):
        """
        use during configuration
        """
        if (n not in self.mOutputs):
            self.mOutputs.append(n)


    def initialize(self):
        inputCount = len(self.mInputs)
        # TODO: compare with He initialization
        weightStdDev = np.sqrt(1.0 / inputCount)
        self.mInputWeights = np.random.normal(0.0, weightStdDev, inputCount)
        self.mInputBias = np.random.normal(0.0, 1.0)

        self.mDeltaInputWeights = np.zeros(inputCount)
        self.mDeltaInputBias = 0.0
        self.mSampleCount = 0

    def feedforward(self):
        """
        :return activation of the neuron
        """
        self.mLatestInputs = np.array([n.getLatestActivation() for n in self.mInputs])
        #print("mLatestInputs = ", self.mLatestInputs)
        #print("mInputWeights = ", self.mInputWeights)
        #print("mInputBias = ", self.mInputBias)
        z = np.dot(self.mLatestInputs, self.mInputWeights) + self.mInputBias
        self.mLatestActivation = self.mActivationFunction.getValue(z)
        self.mLatestActivationDerivative = self.mActivationFunction.getDerivative(z)
        return self.mLatestActivation


    def backPropagate(self):
        """
        :return cost partial derivateive
        """
        par_C_over_par_a = \
                np.sum([n.getLatestCostPartialDerivative() * n.getInputWeight(self.mId) for n in self.mOutputs])

        # par_C_over_par_z = par_C_over_par_a * d_a_over_d_z
        self.mLatestCostPartialDerivative = par_C_over_par_a * self.mLatestActivationDerivative

        self.mDeltaInputWeights += self.mLatestCostPartialDerivative * self.mLatestInputs
        self.mDeltaInputBias += self.mLatestCostPartialDerivative
        self.mSampleCount += 1
        return self.mLatestCostPartialDerivative


    def update(self, learningRate):
        """
        update parameters using gradient descent
        """
        if (0 == self.mSampleCount):
            return

        k = learningRate / self.mSampleCount
        self.mInputWeights -= k * self.mDeltaInputWeights
        self.mInputBias -= k * self.mDeltaInputBias

        # prepare for the next update
        self.mDeltaInputWeights = np.zeros(len(self.mInputWeights))
        self.mDeltaInputBias = 0.0
        self.mSampleCount = 0


    def print(self):
        print(f"[neuron] id = {self.mId}, tag = {self.mTag}")
        print(f"    {len(self.mInputs)} inputs: {[n.id for n in self.mInputs]}")
        print(f"    {len(self.mOutputs)} outputs:  {[n.id for n in self.mOutputs]}")


class InputNode(Node):
    def __init__(self, id):
        Node.__init__(self, id, ActivationFunction.Linear, "input")

    def initialize(self):
        pass

    def feedforward(self, x):
        self.mLatestActivation = x
        return self.mLatestActivation

    def backPropagate(self):
        pass

    def update(self, learningRate):
        pass

class OutputNode(Node):
    def __init__(self, id, activationFunction):
        Node.__init__(self, id, activationFunction, "output")

    def backPropagate(self, costPartialDerivative):
        self.mLatestCostPartialDerivative = costPartialDerivative

        self.mDeltaInputWeights += self.mLatestCostPartialDerivative * self.mLatestInputs
        self.mDeltaInputBias += self.mLatestCostPartialDerivative
        self.mSampleCount += 1
        return self.mLatestCostPartialDerivative

class Graph:
    def __init__(self):
        # only indices
        self.mInputNodes = []
        self.mOutputNodes = []
        # all hidden nodes sorted topologically
        self.mHiddenNodes = []
        self.mCostFunction = None

        self.mBatchSize = 1
        self.mLearningRate = 0.1
        self.mMaxEpoch = 30

    def saveToFile(self, filename):
        print(f"saving to file '{filename}'")
        with open(filename, "wb") as f:
            pickle.dump(self.__dict__, f)
        print("done")

    def loadFromFile(self, filename):
        print(f"loading from file '{filename}'")
        with open(filename, "rb") as f:
            d = pickle.load(f)
            self.__dict__.update(d)
        print("done")

    def initialize(self, jsonStr):
        """
        JSON format:
        {
            "graph": {
                "nodes": array of Node
                "edges": array of Edge,
                "cost_function": str
            },
            "hyperparameters": {
                "learning_rate": float
                "batch_size": int
                "max_epoch": int
            }
        }

        where:
        Node:
        {
            "id": int ( must be unique )
            "activation_function": str ( "sigmoid", "tanh", "relu", "softplus", "linear" )
            "tag": str ( "input", "output", "hidden" )
        }

        Edge:
            [ int, int ]
        ID of the from source node and estination node, respectively

        cost_function: one of ( "quadratic", "cross_entropy" )

        """
        root = json.loads(jsonStr)
        if (not isinstance(root, dict)):
            raise InputError("Invalid JSON format")
        graph = root["graph"]
        hyperparameters = root["hyperparameters"]

        # parse graph
        nodes = {}
        for n in graph["nodes"]:
            id = int(n["id"])
            if (id in nodes):
                raise InputError(f"Duplicated node id {id}")

            af = n["activation_function"]
            tag = n["tag"]
            if ("input" == tag):
                nodes.update({id: InputNode(id)})
                self.mInputNodes.append(nodes[id])
            elif ("output" == tag):
                nodes.update({id: OutputNode(id, ActivationFunction.create(af))})
                self.mOutputNodes.append(nodes[id])
            elif ("hidden" == tag):
                nodes.update({id: Node(id, ActivationFunction.create(af), tag)})
            else:
                raise InputError(f"Unsupported node tag {tag}")

        edges = graph["edges"]
        indegrees = [set() for i in range(len(nodes))]
        for e in edges:
            src = e[0]
            dst = e[1]
            nodes[src].registerOutput(nodes[dst])
            nodes[dst].registerInput(nodes[src])

            indegrees[dst].add(src)


        self.mCostFunction = CostFunction.create(graph["cost_function"])

        # parse hyperparameters
        self.mLearningRate = float(hyperparameters["learning_rate"])
        self.mBatchSize = int(hyperparameters["batch_size"])
        self.mMaxEpoch = int(hyperparameters["max_epoch"])

        # topological sort
        nodeCount = len(nodes)
        hiddenNodeCount = nodeCount - len(self.mInputNodes) - len(self.mOutputNodes)
        processed = [False for i in range(nodeCount)]

        for n in self.mInputNodes:
            id = n.id
            processed[id] = True
            for j in range(nodeCount):
                indegrees[j].discard(id)

        self.mHiddenNodes.clear()
        for i in range(hiddenNodeCount):
            id = None
            for j in range(nodeCount):
                if ((not processed[j]) and (len(indegrees[j]) == 0)):
                    id = j
                    break
            if (id is None):
                raise RuntimeError("Not a valid graph")

            processed[id] = True
            self.mHiddenNodes.append(nodes[id])
            for j in range(nodeCount):
                indegrees[j].discard(id)

        # initialize nodes
        for n in self.mInputNodes:
            n.initialize()
        for n in self.mHiddenNodes:
            n.initialize()
        for n in self.mOutputNodes:
            n.initialize()

    def feedforward(self, x):
        """
        :param [in] x: input
        :return yHat: prediction
        """
        for (i, n) in enumerate(self.mInputNodes):
            n.feedforward(x[i])

        for n in self.mHiddenNodes:
            n.feedforward()

        for n in self.mOutputNodes:
            n.feedforward()

        yHat = np.array([n.getLatestActivation() for n in self.mOutputNodes])
        return yHat


    def backPropagate(self, dC_over_dyHat):
        for (i, n) in enumerate(self.mOutputNodes):
            n.backPropagate(dC_over_dyHat[i])

        for n in reversed(self.mHiddenNodes):
            n.backPropagate()


    def update(self):
        for n in self.mOutputNodes:
            n.update(self.mLearningRate)

        for n in self.mHiddenNodes:
            n.update(self.mLearningRate)


    def train(self, xs, ys):
        """
        :param [in] xs: input; each row represents an input
        :param [in] ys: ground truth output; each row represents an output
        """
        print("training")
        indices = np.arange(xs.shape[0])
        for epoch in range(self.mMaxEpoch):
            startTime = time.time()

            np.random.shuffle(indices)
            for i in range(xs.shape[0]):

                yHat = self.feedforward(xs[indices[i], :])

                dC_over_dyHat = self.mCostFunction.getDerivative(ys[indices[i], :], yHat)

                self.backPropagate(dC_over_dyHat)

                if ((1 + i) % self.mBatchSize == 0):
                    self.update()
                    #labels = np.zeros(4)
                    #labels[np.argmax(yHat)] = 1
                    #print(xs[indices[i], :], " --> ", ys[indices[i], :], " --> ", labels)
            self.update()

            endTime = time.time()

            accuracy = self.validate(xs, ys)

            print(f"==> epoch %d: time = %.2fs, accuracy = %.2f%%" %
                    (epoch, endTime - startTime, accuracy * 100))

    def validate(self, xs, ys):
        """
        :return: accuracy
        """
        yHats = np.array([self.feedforward(x) for x in xs])
        labels = Utils.getPredictions(yHats)
        #for (y, l) in zip(ys, labels):
        #    print(y, " --> ", l)
        accuracy = Utils.compare(labels, ys)

        return accuracy


    def print(self):
        print(f"[graph] %d input nodes, %d hidden nodes, %d output nodes, %s cost function" % (
            len(self.mInputNodes),
            len(self.mHiddenNodes),
            len(self.mOutputNodes),
            self.mCostFunction.getName()))

        for n in self.mInputNodes:
            n.print()
        for n in self.mHiddenNodes:
            n.print()
        for n in self.mOutputNodes:
            n.print()


class Trainer(ModelTrainerBase.ModelTrainerBase):
    def __init__(self, dataset, config):
        self.mGraph = Graph()
        ModelTrainerBase.__init__(self)

    def parseConfig(self, config):
        with open(config, "r") as f:
            jsonStr = f.read()
            self.mGraph.initialize(jsonStr)

    def trainModel(self):
        pass

    def getResult(self):
        pass


if (__name__ == "__main__"):
    g = Graph()
    with open("node-graph-sample.json", "r") as f:
        jsonStr = f.read()
        g.initialize(jsonStr)

    g.print()

    # input: 4 values between 0 and 1
    # output: which pixel is max
    count = 10000
    xs = np.random.random((count, 4))
    ys = Utils.getPredictions(xs)

    #print("input and output")
    #for (x, y) in zip(xs, ys):
    #    print(x, " --> ", y)

    g.train(xs, ys)
