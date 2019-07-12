#!/bin/bash

workers=20
dataset_dir="../dataset/elf/x64_small/training"
out_model="/mnt/cache/models/x64_small"
bin_list="$dataset_dir/bin_list.txt"
bin_dir="$dataset_dir/stripped/"
debug_dir="$dataset_dir/debug/"
out_model_var="$out_model/variable/"
out_model_crf="$out_model/crf/model"
log_dir="$out_model/log"
n2p_train="~/debin/Nice2Predict/bazel-bin/n2p/training/train_json"

if [ ! -d "/mnt/cache/bap" ]; then
	mkdir /mnt/cache/bap
	rm -rf ~/.cache/bap
	ln -s /mnt/cache/bap ~/.cache/bap
fi

mkdir -p $out_model_var $out_model_crf $log_dir
export BAP_LOG_DIR="/home/mf/.cache/bap/log"

echo "STARTING VARIABLE TRAINING" &&
	python3 py/train_variable.py \
		--bin_list $bin_list \
		--bin_dir $bin_dir \
		--debug_dir $debug_dir \
		--out_model $out_model_var \
		--workers $workers \
		--reg_num_f 1000 \
		--off_num_f 1000 &&
	echo "STARTING CRF TRAINING" &&
	python3 py/train_crf.py \
		--bin_list $bin_list \
		--bin_dir $bin_dir \
		--debug_dir $debug_dir \
		--out_model $out_model_crf \
		--log_dir $log_dir \
		--workers $workers \
		--n2p_train $n2p_train \
		--valid_labels c_valid_labels
