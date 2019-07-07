#/bin/bash
dataset_dir="../dataset/elf/x64/training"
out_model="/dev/shm/models"
bin_list="$dataset_dir/bin_list.txt"
bin_dir="$dataset_dir/stripped/"
debug_dir="$dataset_dir/debug/"
out_model_var="$out_model/variable/x64/"
out_model_crf="$out_model/crf/x64/model"
valid_labels="../c_valid_labels"
log_dir="$out_model/log"

n2p_train="~/debin/Nice2Predict/bazel-bin/n2p/training/train_json"

echo "Starting n2p server" &&
    cd Nice2Predict &&
    ./bazel-bin/n2p/json_server/json_server \
        --port 8604 \
        --model $out_model_crf \
        --valid_labels $valid_labels \
        -logtostderr &
cd ..

echo "Predicting debug info for example binary lcrack" &&
    python3 py/predict.py \
        --binary "examples/stripped/lcrack" \
        --output "./lcrack.output" \
        --elf_modifier "cpp/modify_elf.so" \
        -two_pass \
        --fp_model $out_model_var \
        --n2p_url "http://localhost:8604" &&
    readelf -S lcrack.output

# echo "Starting evaluation for test dataset" &&
#     python3 py/evaluate.py \
#         --binary 