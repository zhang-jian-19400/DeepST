# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import os
import cPickle as pickle
import time
from copy import copy
import numpy as np
import h5py

from keras.optimizers import Adam  # , Nadam
from keras.callbacks import EarlyStopping, ModelCheckpoint

# from deepst_flow.models.STConvolution import seqCNN_CPTM
from deepst_flow.models.STResNet import seqResNet_CPTM
from deepst_flow.datasets import load_stdata, stat
from deepst_flow.preprocessing import MinMaxNormalization
from deepst_flow.preprocessing import remove_incomplete_days
from deepst_flow.config import Config
from deepst_flow.datasets.STMatrix import STMatrix
from deepst_flow.preprocessing import timestamp2vec
import deepst_flow.metrics as metrics
np.random.seed(1337)  # for reproducibility

# parameters
DATAPATH = Config().DATAPATH


def load_data(T=48, nb_flow=2, len_closeness=None, len_period=None, len_trend=None, len_test=None, preprocess_name='preprocessing.pkl'):
    assert(len_closeness + len_period + len_trend > 0)
    # load data
    # 2015.03.01: Sunday
    # 13 - 16

    data, timestamps = load_stdata(os.path.join(DATAPATH, 'loop_gy16.h5'))
    print(timestamps)
    # remove a certain day which does not have 48 timestamps
    data, timestamps = remove_incomplete_days(data, timestamps, T)
    data = data[:, :nb_flow]
    data[data < 0] = 0.
    data_all = [data]
    timestamps_all = [timestamps]
    # minmax_scale
    data_train = data[:-len_test]
    print('train_data shape: ', data_train.shape)
    mmn = MinMaxNormalization()
    mmn.fit(data_train)
    data_all_mmn = []
    for d in data_all:
        data_all_mmn.append(mmn.transform(d))

    fpkl = open('preprocessing.pkl', 'wb')
    for obj in [mmn]:
        pickle.dump(obj, fpkl)
    fpkl.close()

    XC, XP, XT = [], [], []
    Y = []
    timestamps_Y = []
    for data, timestamps in zip(data_all_mmn, timestamps_all):
        # instance-based dataset --> sequences with format as (X, Y) where X is a sequence of images and Y is an image.
        st = STMatrix(data, timestamps, T, CheckComplete=False)
        _XC, _XP, _XT, _Y, _timestamps_Y = st.toSeq4(len_closeness=len_closeness, len_period=len_period, len_trend=len_trend)
        XC.append(_XC)
        XP.append(_XP)
        XT.append(_XT)
        Y.append(_Y)
        timestamps_Y += _timestamps_Y

    # load meta feature
    meta_feature = timestamp2vec(timestamps_Y)
    metadata_dim = meta_feature.shape[1]

    XC = np.vstack(XC)
    XP = np.vstack(XP)
    XT = np.vstack(XT)
    Y = np.vstack(Y)
    print("XC shape: ", XC.shape, "XP shape: ", XP.shape, "XT shape: ", XT.shape, "Y shape:", Y.shape)

    XC_train, XP_train, XT_train, Y_train = XC[:-len_test], XP[:-len_test], XT[:-len_test], Y[:-len_test]
    XC_test, XP_test, XT_test, Y_test = XC[-len_test:], XP[-len_test:], XT[-len_test:], Y[-len_test:]
    meta_feature_train, meta_feature_test = meta_feature[:-len_test], meta_feature[-len_test:]

    X_train = []
    X_test = []
    for l, X_ in zip([len_closeness, len_period, len_trend], [XC_train, XP_train, XT_train]):
        if l > 0:
            X_train.append(X_)
    for l, X_ in zip([len_closeness, len_period, len_trend], [XC_test, XP_test, XT_test]):
        if l > 0:
            X_test.append(X_)
    print('train shape:', XC_train.shape, Y_train.shape, 'test shape: ', XC_test.shape, Y_test.shape)

    X_train.append(meta_feature_train)
    X_test.append(meta_feature_test)
    for _X in X_train:
        print(_X.shape, )
    print()
    for _X in X_test:
        print(_X.shape, )
    print()
    return X_train, Y_train, X_test, Y_test, mmn, metadata_dim
