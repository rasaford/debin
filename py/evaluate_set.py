import argparse
import os
import json
import subprocess
import multiprocessing


from evaluate import evaluate_binary


def get_args():
    parser = argparse.ArgumentParser(
        description='Evaluate a set of stripped binaries')
    parser.add_argument('--bin_list', type=str, required=True,
                        help='List of binary names to evaluate')
    parser.add_argument('--bin_dir', type=str, required=True,
                        help='Directory of stripped binares to evaluate')
    parser.add_argument('--debug_dir', type=str, required=True,
                        help='Directory of binaries with debug symbols')
    parser.add_argument('--bap', dest='bap', type=str, default='',
                        help='path of cached BAP-IR file.')
    parser.add_argument('-two_pass', dest='two_pass', action='store_true', default=False,
                        help='whether to use two passes (variable classification and structured prediction). Setting it to false only will only invoke structured prediction.')
    parser.add_argument('--classifier', type=str, required=True,
                        help='Path of the models for the first pass (variable classification).')
    parser.add_argument('--n2p_url', type=str, required=True,
                        help='URL of n2p server.')
    parser.add_argument('--log_dir', type=str, required=True,
                        help='Temporary directory to save log stat files of individual binaries to')
    parser.add_argument('--workers', type=int, default=1)
    return parser.parse_args()


def run_eval(binary, bap, debug_info, n2p_url, stat, two_pass, fp_model):
    if not os.path.isfile(stat):
        print('not file ' + stat)
        evaluate_binary(binary, bap, debug_info, n2p_url,
                        stat, two_pass, fp_model)
        print('evaluated binary {}, loading results...'.format(binary))

    with open(stat) as f:
        data = json.load(f)
    return data


def main():
    args = get_args()
    with open(args.bin_list) as f:
        binaries = list(map(lambda l: l.strip('\r\n'), f.readlines()))

    with multiprocessing.Pool(args.workers) as pool:
        arguments = [(os.path.join(args.bin_dir, bin), args.bap,
                      os.path.join(args.debug_dir, bin), args.n2p_url,
                      os.path.join(args.log_dir, bin + '.json'),
                      args.two_pass, args.classifier) for bin in binaries]
        results = [x for x in pool.starmap(run_eval, arguments) if x]

    name = [n for n in sorted(os.listdir(os.path.dirname(args.log_dir)))][-1]
    results_path = os.path.join(args.log_dir, name + '.json')
    print('done evaluating binaries, writing results to {}'.format(results_path))
    with open(results_path, 'w') as f:
        json.dump(results, f)


if __name__ == '__main__':
    main()
