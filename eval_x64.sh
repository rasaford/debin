#!/bin/bash
workers=10
port=$(shuf -i 2000-65000 -n 1)
model_dir="/mnt/cache/models/x64"
dataset_dir="../dataset/elf/x64/testing"

classifier="$model_dir/variable"
crf_model_dir="$model_dir/crf/model"
bin_list="$dataset_dir/bin_list.txt"
bin_dir="$dataset_dir/stripped"
debug_dir="$dataset_dir/debug"
log_dir="$model_dir/eval"

bap_cache="/home/mf/.cache/bap"
n2p_url="http://localhost:$port"

elf_modifier="~/debin/cpp/modify_elf.so"

mkdir -p $log_dir

cd Nice2Predict
./bazel-bin/n2p/json_server/json_server \
	--port $port \
	--model $crf_model_dir \
	--valid_labels ../c_valid_labels \
	-logtostderr &
cd ..
sleep 20 &&
    cat $bin_list | xargs -I % -P$workers sh -c "python3 py/evaluate.py --binary $bin_dir/% --debug_info $debug_dir/% -two-pass --n2p_url $n2p_url --stat $log_dir/% --output $log_dir/%.output --elf_modifier $elf_modifier" &&
    # python3 py/evaluate_set.py \
    #     --bin_list $bin_list \
    #     --bin_dir $bin_dir \
    #     --debug_dir $debug_dir \
    #     -two_pass \
    #     --classifier $classifier \
    #     --n2p_url $n2p_url \
    #     --log_dir $log_dir \
	# --workers $workers &&
	tar -czf $model_dir/eval_$(date +%Y-%m-%d_%H-%M-%S).tar.gz $log_dir
