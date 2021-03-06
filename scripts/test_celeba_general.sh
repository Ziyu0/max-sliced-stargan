#!/bin/bash

# Test the model on all images from the test dataset

DATASET="CelebA"
IMAGE_SIZE=128                      # Must be the same size when you train it
C_DIM=3
SELECTED_ATTRS=("Blond_Hair" "Male" "Young")
CUDA_DEVICE_NAME="cuda:1"

EXP_ROOT_DIR="stargan_celeba_1"     # Root dir of the ckpt to be loaded
BATCH_SIZE=16                       # Use a small number so that the output images won't be too big
TEST_ITERS=100000                   # Part of the name of the ckpt

cd ..
python main.py \
--mode test \
--dataset $DATASET \
--image_size $IMAGE_SIZE \
--sample_dir "$EXP_ROOT_DIR/samples" \
--log_dir "$EXP_ROOT_DIR/logs" \
--model_save_dir "$EXP_ROOT_DIR/models" \
--result_dir "$EXP_ROOT_DIR/results_$TEST_ITERS" \
--config_dir "$EXP_ROOT_DIR/configs" \
--progress_dir "$EXP_ROOT_DIR/progress" \
--c_dim $C_DIM \
--selected_attrs ${SELECTED_ATTRS[*]} \
--cuda_device_name $CUDA_DEVICE_NAME \
--batch_size $BATCH_SIZE \
--test_iters $TEST_ITERS