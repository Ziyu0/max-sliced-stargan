#!/bin/bash

# exp_types = {
#     0: 'stargan_celeba',
#     1: 'stargan_celeba_sw',
#     2: 'stargan_celeba_sw_d',
#     3: 'stargan_celeba_max_sw'   
# }
EXP_ROOT="./"
PLOT_ROOT="./plots"

EXP_TYPE_ID=3           # See keys of the exp_types above
EXP_IDS=(1 2 3 4)

LABEL_ATTR="d_loss"

LABEL_VALS=("1-BCE" "2-WGAN-GP" "3-WGAN-GP" "4-WGAN-GP")      # Must align with exp_ids


python utils/plots.py \
--exp_root $EXP_ROOT \
--plot_root $PLOT_ROOT \
--exp_type_id $EXP_TYPE_ID \
--exp_ids ${EXP_IDS[*]} \
--label_attr $LABEL_ATTR \
--label_vals ${LABEL_VALS[*]}