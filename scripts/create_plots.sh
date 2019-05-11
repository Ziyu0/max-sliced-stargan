#!/bin/bash

# Create loss plots.

# exp_types = {
#     0: 'stargan_celeba',
#     1: 'stargan_celeba_sw',
#     2: 'stargan_celeba_sw_d',
#     3: 'stargan_celeba_max_sw'   
# }

EXP_ROOT="./"
PLOT_ROOT="./plots"

EXP_TYPE_ID=3           # See keys of the exp_types above
EXP_IDS=(5 9 10)

LABEL_ATTR="sample_size"
LABEL_VALS=("16" "32" "64")

cd ..
python utils/plots.py \
--exp_root $EXP_ROOT \
--plot_root $PLOT_ROOT \
--exp_type_id $EXP_TYPE_ID \
--exp_ids ${EXP_IDS[*]} \
--label_attr $LABEL_ATTR \
--label_vals ${LABEL_VALS[*]}