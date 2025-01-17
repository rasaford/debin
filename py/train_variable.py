import os
import pickle
import random
import argparse
import multiprocessing
import gzip
import traceback

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
            return b.get_features()
    except Exception as e:
        print('Exception in binary anaylsis: ' + e)
        return [], [], [], []


def train(X_raw, Y_raw, num_p, num_n, num_f, n_estimators, n_jobs, name, output_dir):
    X, Y = [], []
    i_p, i_n = 0, 0

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
    print('fitting DictVectorizer')
    dict_vec = dict_vec.fit(X)
    with open(dict_path, 'wb') as dict_file:
        pickle.dump(dict_vec, dict_file)

    X_dict = X
    X = dict_vec.transform(X)

    print('fitting SelectKBest')
    support = SelectKBest(chi2, k=num_f).fit(X, Y)
    with open(support_path, 'wb') as support_file:
        pickle.dump(support, support_file)

    dict_vec.restrict(support.get_support())
    X = dict_vec.transform(X_dict)

    model = ExtraTreesClassifier(n_estimators=n_estimators, n_jobs=n_jobs)
    print('fitting ExtraTreesClassifier')

    model = model.fit(X, Y)
    with open(model_path, 'wb') as model_file:
        pickle.dump(model, model_file)
    print('done training {}'.format(name))


def block_process(bins, args):
    block_size = args.workers // 2
    blocks = [bins[i: i + block_size] for i in range(0, len(bins), block_size)]

    def block_path(i): return os.path.join(args.out_model, '{}.block'.format(i))

    for i, block in enumerate(blocks):
        path = block_path(i)
        if os.path.isfile(path):
            print('skipping bap analysis for {}'.format(path))
            continue

        with multiprocessing.Pool(args.workers // 2) as pool:
            arguments = [(b, args.bin_dir, args.debug_dir, args.bap_dir)
                         for b in block]
            results = pool.starmap(generate_feature, arguments)
        print('writing block {} to {}'.format(i, path))
        with gzip.open(path, 'wb') as f:
            pickle.dump(results, f)

    results = []
    for i, _ in enumerate(blocks):
        path = block_path(i)
        print('reading block {}'.format(path))
        with gzip.open(path, 'rb') as f:
            results = results + pickle.load(f)
    print('ran bap for {} binaries'.format(len(results)))
    return results


def main():
    args = get_args()

    with open(args.bin_list) as f:
        bins = list(map(lambda l: l.strip('\r\n'), f.readlines()))

    # with multiprocessing.Pool(args.workers) as pool:
    #     arguments = []
    #     for b in bins:
    #         arguments.append((b, args.bin_dir, args.debug_dir, args.bap_dir))
    #     results = pool.starmap(generate_feature, arguments)
    results = block_process(bins, args)
    random.shuffle(results)

    flatten = lambda l: [item for sublist in l for item in sublist]

    reg_x, reg_y, off_x, off_y = zip(*results)
    reg_x = flatten(reg_x)
    reg_y = bytearray(flatten(reg_y))
    off_x = flatten(off_x)
    off_y = bytearray(flatten(off_y))

    if not os.path.exists(args.out_model):
        os.makedirs(args.out_model)

    train(reg_x, reg_y, args.reg_num_p, args.reg_num_n, args.reg_num_f,
          args.n_estimators, args.workers, 'reg', args.out_model)
    train(off_x, off_y, args.off_num_p, args.off_num_n, args.off_num_f,
          args.n_estimators, args.workers, 'off', args.out_model)


if __name__ == '__main__':
    main()
