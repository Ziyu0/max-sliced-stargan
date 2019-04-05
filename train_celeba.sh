#!/bin/bash

DATASET="CelebA"
IMAGE_SIZE=64
EXP_ROOT_DIR="stargan_celeba_1"

CUDA_DEVICE_NAME="cuda:1"

C_DIM=3
SELECTED_ATTRS=("Blond_Hair" "Male" "Young")

python main.py \
--mode train \
--dataset $DATASET \
--image_size $IMAGE_SIZE \
--sample_dir "$EXP_ROOT_DIR/samples" \
--log_dir "$EXP_ROOT_DIR/logs" \
--model_save_dir "$EXP_ROOT_DIR/models" 
--result_dir "$EXP_ROOT_DIR/results" \
--config_dir "$EXP_ROOT_DIR/configs" \
--c_dim $C_DIM \
--selected_attrs ${SELECTED_ATTRS[*]} \
--cuda_device_name $CUDA_DEVICE_NAME