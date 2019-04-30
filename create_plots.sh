#!/bin/bash

# exp_types = {
#     0: 'stargan_celeba',
#     1: 'stargan_celeba_sw',
#     2: 'stargan_celeba_sw_d',
#     3: 'stargan_celeba_max_sw'   
# }
EXP_ROOT="./"
PLOT_ROOT="./plots"

EXP_TYPE_ID=2           # See keys of the exp_types above
EXP_IDS=(2 6 7)
# EXP_IDS=(1 2 3 4)

# LABEL_ATTR="d_loss"
LABEL_ATTR="multi_settings_2"

# LABEL_VALS=("1-BCE" "2-WGAN-GP" "3-WGAN-GP" "4-WGAN-GP")      # Must align with exp_ids
# LABEL_VALS=("2-size-64" "6-size-128" "7-size-128-proj-20000" "8-size-64-WGP")
LABEL_VALS=("2-size-64" "6-size-128" "7-size-128-proj-20000")



python utils/plots.py \
--exp_root $EXP_ROOT \
--plot_root $PLOT_ROOT \
--exp_type_id $EXP_TYPE_ID \
--exp_ids ${EXP_IDS[*]} \
--label_attr $LABEL_ATTR \
--label_vals ${LABEL_VALS[*]}