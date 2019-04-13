#!/bin/bash

DATASET="CelebA"
IMAGE_SIZE=64
N_CRITIC=5
C_DIM=3
SELECTED_ATTRS=("Blond_Hair" "Male" "Young")
CUDA_DEVICE_NAME="cuda:1"
RESUME_ITERS=0        # 0 means not resume

EXP_ROOT_DIR="stargan_celeba_sw_1"
USE_SW_LOSS=True
BATCH_SIZE=128
NUM_ITERS=10000
NUM_ITERS_DECAY=5000  # 0 means not decay, 5000 means LR will be decayed in the last 5000 iters
NUM_PROJECTIONS=10000
MODEL_SAVE_STEP=5000  # One ckpt is about ~200M, so don't save too many ckpts


# Train
python main.py \
--mode train \
--dataset $DATASET \
--image_size $IMAGE_SIZE \
--sample_dir "$EXP_ROOT_DIR/samples" \
--log_dir "$EXP_ROOT_DIR/logs" \
--model_save_dir "$EXP_ROOT_DIR/models" \
--result_dir "$EXP_ROOT_DIR/results" \
--config_dir "$EXP_ROOT_DIR/configs" \
--progress_dir "$EXP_ROOT_DIR/progress" \
--c_dim $C_DIM \
--selected_attrs ${SELECTED_ATTRS[*]} \
--cuda_device_name $CUDA_DEVICE_NAME \
--n_critic $N_CRITIC \
--use_sw_loss $USE_SW_LOSS \
--batch_size $BATCH_SIZE \
--num_iters $NUM_ITERS \
--num_iters_decay $NUM_ITERS_DECAY \
--num_projections $NUM_PROJECTIONS \
--model_save_step $MODEL_SAVE_STEP \
--resume_iters $RESUME_ITERS