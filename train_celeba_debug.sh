#!/bin/bash

DATASET="CelebA"
IMAGE_SIZE=64
N_CRITIC=5
C_DIM=3
SELECTED_ATTRS=("Blond_Hair" "Male" "Young")
CUDA_DEVICE_NAME="cuda:0"
RESUME_ITERS=11000  # 0 means not resume

EXP_ROOT_DIR="stargan_debug"
USE_SW_LOSS=True
USE_D_FEATURE=True              # Compute SWD with D's features
BATCH_SIZE=128
NUM_ITERS=25000
NUM_ITERS_DECAY=25000           # debug decay_learning_rates()
LR_UPDATE_STEP=10               # debug decay_learning_rates()
NUM_PROJECTIONS=10000
MODEL_SAVE_STEP=10              # debug save_checkpoints()
SAMPLE_STEP=10                  # debug translate_samples()


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
--resume_iters $RESUME_ITERS \
--sample_step $SAMPLE_STEP \
--lr_update_step $LR_UPDATE_STEP \
--use_d_feature $USE_D_FEATURE