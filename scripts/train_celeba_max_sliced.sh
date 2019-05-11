#!/bin/bash

# Train the Max-Sliced StarGAN on CelebA dataset

DATASET="CelebA"
IMAGE_SIZE=128
N_CRITIC=5
C_DIM=6
SELECTED_ATTRS=("Black_Hair" "Brown_Hair" "Eyeglasses" "Pale_Skin" "Rosy_Cheeks" "Bags_Under_Eyes")
CUDA_DEVICE_NAME="cuda:0"
RESUME_ITERS=0

EXP_ROOT_DIR="stargan_celeba_max_sw_1"
USE_MAX_SW_LOSS=True
BATCH_SIZE=16
NUM_ITERS=100000
NUM_ITERS_DECAY=0
MODEL_SAVE_STEP=10000

D_CRITERION="WGAN-GP"
# SORT_SCALAR="True"         # Pass scalar to compute max-sliced Wasserstein distance
SORT_SCALAR="False"         # Pass vector to compute max-sliced Wasserstein distance

# Train
cd ..
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
--batch_size $BATCH_SIZE \
--num_iters $NUM_ITERS \
--num_iters_decay $NUM_ITERS_DECAY \
--model_save_step $MODEL_SAVE_STEP \
--resume_iters $RESUME_ITERS \
--d_criterion $D_CRITERION \
--use_max_sw_loss $USE_MAX_SW_LOSS \
--sort_scalar $SORT_SCALAR