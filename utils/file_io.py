import tensorflow as tf
import glob
from collections import defaultdict
import os

def load_single_loss_file(logdir):
    """Load loss data from a single TF event file.

    Args:
        logdir(str): Path of the dir storing the event file, 
            e.g., 'stargan_celeba_sw_d_5/logs'
    Returns:
        loss(dict): Dict, key = loss tag, val = list of losses
    """
    paths = glob.glob(logdir + '/events.*')
    if not paths:
        return None
    
    event_path = paths[0]
    loss = defaultdict(list)
    
    for e in tf.train.summary_iterator(event_path):
        for v in e.summary.value:
            if 'loss' in v.tag:
                loss[v.tag].append(v.simple_value)
    
    return loss

def load_loss_files(root, exp_name, exp_ids):
    """Load all loss files for the same type of experiments.

    Args:
        root(str): Path of the root dir
        exp_name(str): Name of the experiment which is part of the exp dir name,
            such as 'stargan_celeba_max_sw'
        exp_ids(list): List of the IDs of the experiments to be loaded
    Returns:
        loss(dict<dict>): Key = exp name, val = loss dict of this exp
    """
    loss = defaultdict(list)
    
    for exp_id in exp_ids:
        # Get folder in form 'expName_expID/logs', eg, 'stargan_celeba_1/logs'
        exp_dir_name = '{}_{}'.format(exp_name, exp_id)
        exp_path = os.path.join(root, exp_dir_name, 'logs')
        
        # Get loss for each experiment
        single_loss = load_single_loss_file(exp_path)
        if single_loss:
            loss[exp_dir_name].append(single_loss)
    
    return loss

    # 0 - stargan_celeba
    # 1 - stargan_celeba_sw
    # 2 - stargan_celeba_sw_d
    # 3 - stargan_celeba_max_sw
