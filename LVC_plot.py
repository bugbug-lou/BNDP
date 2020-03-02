import numpy as np
import datetime
import random
from matplotlib import pyplot as plt
import multiprocessing
import torch
from torch.autograd import Variable
from torch import optim
from lempel_ziv_complexity import lempel_ziv_complexity
import collections
import argparse


def array_to_string(x):
    y = ''
    for l in x:
        y += str(int(l))
    return y


def output_anal(x):
    a = x.size()[0]
    y = torch.zeros(a)
    for i in range(a):
        if x[i, 0] > x[i, 1]:
            y[i] = 0
        else:
            y[i] = 1
    return y


def get_freq(x):
    T = collections.Counter(x)
    Y = np.array(list(T.values()), dtype=np.longfloat)
    Y = Y / times
    Y = np.sort(Y)
    Y = Y[::-1]
    return Y


def get_max_freq(x):
    T = collections.Counter(x)
    Y = np.array(list(T.values()), dtype=np.longfloat)
    a = np.max(Y)
    for f in list(T.keys()):
        if T[f] == a:
            return f


def get_LVComplexity(x):
    return lempel_ziv_complexity(array_to_string(x))

testtime = 30
Error_nonBN = torch.zeros(testtime)
Error_BN = torch.zeros(testtime)
non_BN_mean_complexity = torch.zeros(testtime)
BN_mean_complexity = torch.zeros(testtime)
for t in range(testtime):
    if t % (testtime / 5) == 0:
        print(f'{datetime.datetime.now()} No.{t} Complete!')
    ## parameters
    epocs = t  ## training time
    times = 50  ## number of sampling
    n = 7  ## dimension of input data, user-defined
    m = 2 ** n  ## number of data points
    k = 2 ** m
    m_2 = 2 ** (n - 1)
    m_3 = 2 ** (n - 2)
    layer_num = 3  ## number of layers of the neural network, user-defined
    neu = 40  ## neurons per layer

    ## initialize data sets as binary strings
    data = np.zeros([m, n])
    for i in range(m):
        bin = np.binary_repr(i, n)
        a = np.array(list(bin), dtype=int)
        data[i, :] = a

    ## Target Function: we choose one that is of intermediate Lempel_Ziv complexity
    target = np.zeros(m)
    for i in range(m_2):
        target[i] = 1
        target[i + m_2] = 0
    data = torch.from_numpy(data)
    target = torch.from_numpy(target)
    target = target.long()

    ## generate training set and inference set
    XTrain = torch.zeros(m_2, n)
    XTest = torch.zeros(m_2, n)
    YTrain = torch.zeros(m_2)
    YTest = torch.zeros(m_2)
    for i in range(m_3):
        XTrain[i, :] = data[i, :]
        XTrain[i + m_3, :] = data[i + m_2, :]
        YTrain[i] = target[i]
        YTrain[i + m_3] = target[i + 3 * m_3]
        XTest[i, :] = data[i + m_3, :]
        XTest[i, :] = data[i + 3 * m_3, :]
        YTest[i] = target[i + m_3]
        YTest[i + m_3] = target[i + 3 * m_3]
    Complexity_train = lempel_ziv_complexity(array_to_string(YTrain))
    Complexity = lempel_ziv_complexity(array_to_string(target))
    YTrain = YTrain.long()
    YTest = YTest.long()

    ## define loss function
    loss = torch.nn.CrossEntropyLoss(size_average=True)


    def train(model, loss, optimizer, inputs, labels):
        model.train()
        inputs = Variable(inputs, requires_grad=False)
        labels = Variable(labels, requires_grad=False)

        # reset gradient
        optimizer.zero_grad()

        # forward loop
        logits = model.forward(inputs)
        output = loss.forward(logits, labels)

        # backward
        output.backward()
        optimizer.step()
        return output.item()


    def get_error(model, inputs, labels):
        model.eval()
        inputs = Variable(inputs, requires_grad=False)
        labels = Variable(labels, requires_grad=False)
        logits = model.forward(inputs)
        predicts = output_anal(logits)
        k = predicts - target
        a = torch.sum(torch.abs(k))
        return a/m


    def predict(model, inputs):
        model.eval()
        inputs = Variable(inputs, requires_grad=False)

        logits = model.forward(inputs)
        return logits


    ## the main program
    L_nonBN = torch.zeros(times)
    L_BN = torch.zeros(times)
    Complexity_agg_BN = torch.zeros(times)
    Complexity_agg = torch.zeros(times)

    h = 0
    while (h < times):
        ## initialize model
        model1 = torch.nn.Sequential()  ## model without batch normalization
        model2 = torch.nn.Sequential()  ## model with batch normalization

        ## add some layers for model 1, this is without BN
        model1.add_module('FC1', torch.nn.Linear(n, neu))
        model1.add_module('relu1', torch.nn.ReLU())
        model1.add_module('FC2', torch.nn.Linear(neu, neu))
        model1.add_module('relu2', torch.nn.ReLU())
        model1.add_module('FC3', torch.nn.Linear(neu, neu))
        model1.add_module('relu2', torch.nn.ReLU())
        model1.add_module('FC4', torch.nn.Linear(neu, neu))
        model1.add_module('relu2', torch.nn.ReLU())
        model1.add_module('FC5', torch.nn.Linear(neu, 2))

        ##model1.add_module('FC4', torch.nn.Linear(neu,1))
        #   #model1.add_module('relu4', torch.nn.ReLU())

        ## add some layers for model 2, this is with BN
        model2.add_module('FC1', torch.nn.Linear(n, neu))
        model2.add_module('bn1', torch.nn.BatchNorm1d(neu))
        model2.add_module('relu1', torch.nn.ReLU())
        model2.add_module('FC2', torch.nn.Linear(neu, neu))
        model2.add_module('bn2', torch.nn.BatchNorm1d(neu))
        model2.add_module('relu2', torch.nn.ReLU())
        model2.add_module('FC3', torch.nn.Linear(neu, 2))

        ## define optimizer
        optimizer1 = optim.SGD(model1.parameters(), lr=0.0001, momentum=0.9)
        optimizer2 = optim.SGD(model2.parameters(), lr=0.0001, momentum=0.9)

        for epoc in range(epocs):
            train(model1, loss, optimizer1, XTrain, YTrain)
            train(model2, loss, optimizer2, XTrain, YTrain)

        data = data.float()
        Aggregate1 = predict(model1, data)
        Aggregate2 = predict(model2, data)
        Output_1 = output_anal(Aggregate1)
        Output_2 = output_anal(Aggregate2)
        L_nonBN[h] = get_error(model1, data, target)
        L_BN[h] = get_error(model2, data, target)
        a = lempel_ziv_complexity(array_to_string(Output_1))
        b = lempel_ziv_complexity(array_to_string(Output_2))
        Complexity_agg[h] = a
        Complexity_agg_BN[h] = b

        h = h + 1

    Error_nonBN[t] = torch.mean(L_nonBN)
    Error_BN[t] = torch.mean(L_BN)
    non_BN_mean_complexity[t] = torch.mean(Complexity_agg)
    BN_mean_complexity[t] = torch.mean(Complexity_agg_BN)
    t = t+1

# plot
fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1)
M = min(min(BN_mean_complexity),min(non_BN_mean_complexity))
Ma = max(max(BN_mean_complexity),max(non_BN_mean_complexity))
T = min(min(Error_BN),min(Error_nonBN))
Ta = max(max(Error_BN),max(Error_nonBN))
X = np.arange(testtime)
ax1.plot(X,Error_nonBN, label="Error, no BatchNorm")
ax1.plot(X,Error_BN, label="Error, BatchNorm")
ax1.legend(loc="upper right")
ax2.plot(X,non_BN_mean_complexity, label="mean complexity, no BatchNorm")
ax2.plot(X,BN_mean_complexity,label="mean complexity, BatchNorm")
ax2.legend(loc="upper right")
plt.savefig('lvc_lc.png')
plt.show()
