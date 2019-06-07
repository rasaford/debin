import os
import pickle
import gzip
import random
import argparse
import multiprocessing
import math
import glob

from sklearn.feature_extraction import DictVectorizer
from sklearn.utils import shuffle
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.feature_selection import SelectKBest, chi2


from common.config import Config
from binary import Binary


def get_args():
    parser = argparse.ArgumentParser('Debin to hack binaries. '
                                     'This script executes the training of variable classification models. '
                                     'Make sure you have enough disk space.')

    parser.add_argument('--bin_list', dest='bin_list', type=str, required=True,
                        help='list of binaries to train.')
    parser.add_argument('--bin_dir', dest='bin_dir', type=str, required=True,
                        help='directory of the stripped binaries.')
    parser.add_argument('--debug_dir', dest='debug_dir', type=str, required=True,
                        help='directory of debug information files.')
    parser.add_argument('--bap_dir', dest='bap_dir', type=str, default='',
                        help='directory of cached BAP-IR files.')
    parser.add_argument('--workers', dest='workers', type=int, default=1,
                        help='number of workers (i.e., parallization).')
    parser.add_argument('--out_model', dest='out_model', type=str, required=True,
                        help='directory of the output models.')
    parser.add_argument('--reg_num_p', dest='reg_num_p', type=int, default=400000,
                        help='number of positive samples used for training the model for registers.')
    parser.add_argument('--reg_num_n', dest='reg_num_n', type=int, default=800000,
                        help='number of negative samples used for training the model for registers.')
    parser.add_argument('--reg_num_f', dest='reg_num_f', type=int, default=10000,
                        help='dimension of features for the model for registers.')
    parser.add_argument('--off_num_p', dest='off_num_p', type=int, default=300000,
                        help='number of positive samples used for training the model for stack offsets.')
    parser.add_argument('--off_num_n', dest='off_num_n', type=int, default=300000,
                        help='number of negative samples used for training the model for stack offsets.')
    parser.add_argument('--off_num_f', dest='off_num_f', type=int, default=10000,
                        help='dimension of features for the model for stack offsets.')
    parser.add_argument('--n_estimators', dest='n_estimators', type=int, default=25,
                        help='number of trees in the models.')

    args = parser.parse_args()
    return args


def generate_feature(b, bin_dir, debug_dir, bap_dir):
    try:
        config = Config()
        config.BINARY_NAME = b
        config.BINARY_PATH = os.path.join(bin_dir, b)
        config.DEBUG_INFO_PATH = os.path.join(debug_dir, b)
        if bap_dir != '':
            config.BAP_FILE_PATH = os.path.join(bap_dir, b)
        with open(config.BINARY_PATH, 'rb') as elffile, open(config.DEBUG_INFO_PATH, 'rb') as debug_elffile:
            b = Binary(config, elffile, debug_elffile)
            f = b.get_features()
            return f
    except Exception as e:
        print('Exception: ' + str(e))
        return None


def train(X_raw, Y_raw, num_p, num_n, num_f, n_estimators, n_jobs, name, output_dir):
    print('starting training')
    X, Y = [], []
    i_p, i_n = 0, 0
    # print([(x[:4], y) for x,y in zip(X_raw, Y_raw)])
    print('positive samples: ' + str(len([y for _, y in zip(X_raw, Y_raw) if y == 1])) + ' negative samples: ' + str(len([y for _, y in zip(X_raw, Y_raw) if y == 0])))

    for x, y in zip(X_raw, Y_raw):
        if i_p < num_p or i_n < num_n:
            if (y == 1 and i_p < num_p) or (y == 0 and i_n < num_n):
                if y == 1:
                    i_p += 1
                else:
                    i_n += 1

                x = dict(map(lambda item: (item, 1), x))
                X.append(x)
                Y.append(y)
        else:
            break
    
    X, Y = shuffle(X, Y)

    dict_path = os.path.join(output_dir, '{}.dict'.format(name))
    support_path = os.path.join(output_dir, '{}.support'.format(name))
    model_path = os.path.join(output_dir, '{}.model'.format(name))
    dict_vec = DictVectorizer(sparse=True)
    dict_vec = dict_vec.fit(X)
    with gzip.open(dict_path, 'wb') as dict_file:
        print('writing dict_file: ' + dict_path)
        pickle.dump(dict_vec, dict_file)

    X_dict = X
    X = dict_vec.transform(X)

    support = SelectKBest(chi2, k=num_f).fit(X, Y)
    with gzip.open(support_path, 'wb') as support_file:
        print('writing support_path: ', support_path)
        pickle.dump(support, support_file)

    dict_vec.restrict(support.get_support())
    X = dict_vec.transform(X_dict)

    model = ExtraTreesClassifier(n_estimators=n_estimators, n_jobs=n_jobs)
    print('fitting ExtraTreesClassifier')
    model = model.fit(X, Y)
    with gzip.open(model_path, 'wb') as model_file:
        print('writing model: ' + model_path)
        pickle.dump(model, model_file)


def analyse_binaries(binaries, bin_dir, debug_dir, bap_dir, out_model, workers):
    def block_path(i): return os.path.join(out_model, 'block_{}.results'.format(i))

    def split_list(l, size):
        res = []
        while len(l) > size:
            res.append(l[:size])
            l = l[size:]
        res.append(l)
        return res

    BLOCK_SIZE = 4*workers

    print('analysing binaries')
    if not os.path.isfile(block_path(0)):
        for i, block in enumerate(split_list(binaries, BLOCK_SIZE)):
            with multiprocessing.Pool(workers) as pool:
                arguments = [(b, bin_dir, debug_dir, bap_dir)
                             for b in block]
                block = [b for b in pool.starmap(generate_feature, arguments) if b]

            block_p = block_path(i)
            with gzip.open(block_p, 'wb') as block_f:
                print('writing block {} of {} to {}'.format(
                    i + 1 , math.ceil(len(binaries) / BLOCK_SIZE), block_p))
                pickle.dump(block, block_f)

    paths = glob.glob(block_path('*'))
    res = []
    for p in reversed(paths):
        print('reading block file {}'.format(p))
        with gzip.open(p, 'rb') as f:
            res += pickle.load(f)
    random.shuffle(res)
    return res


def main():
    args = get_args()
    with open(args.bin_list) as f:
        bins = list(map(lambda l: l.strip('\r\n'), f.readlines()))
    bins.sort()

    if not os.path.exists(args.out_model):
        os.makedirs(args.out_model)

    results = analyse_binaries(
        bins, args.bin_dir, args.debug_dir, args.bap_dir, args.out_model, args.workers)

    reg_x, reg_y, off_x, off_y = zip(*results)
    reg_x, reg_y, off_x, off_y = reg_x[0], reg_y[0], off_x[0], off_y[0]

    train(reg_x, reg_y, args.reg_num_p, args.reg_num_n, args.reg_num_f,
          args.n_estimators, args.workers, 'reg', args.out_model)
    train(off_x, off_y, args.off_num_p, args.off_num_n, args.off_num_f,
          args.n_estimators, args.workers, 'off', args.out_model)


if __name__ == '__main__':
    main()
