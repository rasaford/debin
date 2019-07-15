#!/bin/bash

workers=20
dataset_dir="../dataset/elf/x32/training"
out_model="/mnt/cache/models/x32"
bin_list="$dataset_dir/bin_list.txt"
bin_dir="$dataset_dir/stripped/"
debug_dir="$dataset_dir/debug/"
out_model_var="$out_model/variable"
out_model_crf="$out_model/crf/model"
log_dir="$out_model/log"
n2p_train="~/debin/Nice2Predict/bazel-bin/n2p/training/train_json"

if [ ! -d "/mnt/cache/bap" ]; then
	mkdir /mnt/cache/bap
	rm -rf ~/.cache/bap
	ln -s /mnt/cache/bap ~/.cache/bap
fi

mkdir -p $out_model_var $out_model_crf $log_dir


echo "STARTING VARIABLE TRAINING" &&
	python3 py/train_variable.py \
		--bin_list $bin_list \
		--bin_dir $bin_dir \
		--debug_dir $debug_dir \
		--out_model $out_model_var \
                --reg_num_p 800000 \
                --reg_num_n 1000000 \
                --reg_num_f 20000 \
                --off_num_p 600000 \
                --off_num_n 600000 \
                --off_num_f 20000 \
                --n_estimators 40 \
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
                --max_labels_z 12 \
		--valid_labels c_valid_labels &&
	echo "Archiving model files" &&
	tar -czf $out_model/models_$(date +%Y-%m-%d_%H-%M-%S).tar.gz $out_model_var/off* $out_model_var/reg* $out_model/crf

