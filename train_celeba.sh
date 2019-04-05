#!bin/bash

EXP_DIR="stargan_celeba"

python main.py 
--mode train \
--dataset CelebA \
--image_size 64 \
--c_dim 5 \
--sample_dir "$EXP_DIR/samples" \
--log_dir "$EXP_DIR/logs" \
--model_save_dir "$EXP_DIR/models" 
--result_dir "$EXP_DIR/results" \
--selected_attrs Black_Hair Blond_Hair Brown_Hair Male Young