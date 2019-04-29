#!/bin/bash

# exp_types = {
#     0: 'stargan_celeba',
#     1: 'stargan_celeba_sw',
#     2: 'stargan_celeba_sw_d',
#     3: 'stargan_celeba_max_sw'   
# }
EXP_ROOT="./"
PLOT_ROOT="./plots"

EXP_TYPE_ID=0           # See keys of the exp_types above
EXP_IDS=(1 2 3)

LABEL_ATTR="n_critic"
LABEL_VALS=(5 1 5)      # Must align with exp_ids

DETAIL="just test"
TITLE="${LABEL_ATTR}_${DETAIL}"

python utils/plots.py \
--exp_root $EXP_ROOT \
--plot_root $PLOT_ROOT \
--exp_type_id $EXP_TYPE_ID \
--exp_ids ${EXP_IDS[*]} \
--label_attr $LABEL_ATTR \
--label_vals ${LABEL_VALS[*]} \
--title $TITLE