#!/bin/bash

DATASET="CelebA"
IMAGE_SIZE=64                       # Must be the same size when you train it
C_DIM=3
SELECTED_ATTRS=("Blond_Hair" "Male" "Young")
CUDA_DEVICE_NAME="cuda:1"

EXP_ROOT_DIR="stargan_celeba_sw_d_8"     # Root dir of the ckpt to be loaded
BATCH_SIZE=1                       # MUST use 1 otherwise the specific images may not be loaded correctly
TEST_ITERS=100000                   # Part of the name of the ckpt

TEST_TYPE='small'
TEST_IMG_NUMBERS=(10 165)

# Train
python main.py \
--mode test \
--dataset $DATASET \
--image_size $IMAGE_SIZE \
--sample_dir "$EXP_ROOT_DIR/samples" \
--log_dir "$EXP_ROOT_DIR/logs" \
--model_save_dir "$EXP_ROOT_DIR/models" \
--result_dir "$EXP_ROOT_DIR/results_${TEST_ITERS}_${TEST_TYPE}" \
--config_dir "$EXP_ROOT_DIR/configs" \
--progress_dir "$EXP_ROOT_DIR/progress" \
--c_dim $C_DIM \
--selected_attrs ${SELECTED_ATTRS[*]} \
--cuda_device_name $CUDA_DEVICE_NAME \
--batch_size $BATCH_SIZE \
--test_iters $TEST_ITERS \
--test_type $TEST_TYPE \
--test_img_numbers ${TEST_IMG_NUMBERS[*]}