#!bin/bash

EXP_DIR="stargan_celeba"
# It seems that "$EXP_DIR/samples" is not working
# because the output folder is still "stargan/samples"
# which is the default value

# --selected_attrs Black_Hair Blond_Hair Brown_Hair Male Young

python main.py 
--mode train \
--dataset CelebA \
--image_size 64 \
--sample_dir "$EXP_DIR/samples" \
--log_dir "$EXP_DIR/logs" \
--model_save_dir "$EXP_DIR/models" 
--result_dir "$EXP_DIR/results" \
--c_dim 3 \
--selected_attrs Blond_Hair Male Young \
--cuda_device_name 'cuda:1'