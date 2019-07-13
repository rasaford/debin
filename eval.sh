#!/bin/bash
workers=10
port=8604
model_dir="/mnt/cache/models/x64_mid"
dataset_dir="../dataset/elf/x64_mid/testing"

classifier="$model_dir/variable"
crf_model_dir="$model_dir/crf/model"
bin_list="$dataset_dir/bin_list.txt"
bin_dir="$dataset_dir/stripped"
debug_dir="$dataset_dir/debug"
log_dir="$model_dir/eval"

bap_cache="/home/mf/.cache/bap"
n2p_url="http://localhost:$port"

mkdir -p $log_dir

# cd Nice2Predict
# ./bazel-bin/n2p/json_server/json_server \
#     --port $port \
#     --model $crf_model_dir \
#     --valid_labels ../c_valid_labels \
#     -logtostderr &
# cd ..
#sleep 5 &&
    python3 py/evaluate_set.py \
        --bin_list $bin_list \
        --bin_dir $bin_dir \
        --debug_dir $debug_dir \
        -two_pass \
        --classifier $classifier \
        --n2p_url $n2p_url \
        --log_dir $log_dir \
	--workers $workers
