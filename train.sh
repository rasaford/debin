#!/bin/bash

workers=20
dataset_dir="../dataset/elf/x64/training"
model_dir="/dev/shm/models"
bin_list="$dataset_dir/bin_list.txt"
bin_dir="$dataset_dir/stripped/"
debug_dir="$dataset_dir/debug/"
out_model_var="$model_dir/variable/x64/"
out_model_crf="$model_dir/crf/x64/model"
n2p_train="Nice2Predict/bazel-bin/n2p/training/train_json"
log_dir="new_models/crf"

echo "STARTING VARIABLE TRAINING" &&
python3 py/train_variable.py \
	--bin_list $bin_list \
	--bin_dir $bin_dir \
	--debug_dir $debug_dir \
	--out_model $out_model_var \
	--workers $workers &&
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
