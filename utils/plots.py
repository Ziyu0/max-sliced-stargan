"""Tools to create plots.

Created on April 20, 2019
Updated on
@author: Ziyu
"""

import matplotlib.pyplot as plt
import numpy as np
import argparse
import os

from file_io import load_loss_files

def plot_all_loss(log_step, all_loss, plot_dir, 
                  plot_name, title, labels):
    """
    Note that only loss of the same type of experiments can be put together
    """

    # Leave the color as default?
    
    pass

def main(args):
    # Get the experiments to be loaded
    exp_types = {
        0: 'stargan_celeba',
        1: 'stargan_celeba_sw',
        2: 'stargan_celeba_sw_d',
        3: 'stargan_celeba_max_sw'   
    }
    exp_name = exp_types[args.exp_type_id]
    exp_ids = list(map(int, args.exp_ids))

    # Get all the loss
    all_loss = load_loss_files(args.exp_root, exp_name, exp_ids)

    # Create labels for the plot, such as 'n_critic = 5'
    labels = []
    for val in args.label_vars:
        labels.append('{} = {}'.format(args.label_attr, val))
    
    # Get subdir to save the plots, eg, 'plots/stargan_celeba[n_critic]'
    plot_dir = '{}/{}_[{}]'.format(args.plot_root, exp_name, args.label_attr)
    # Create directories if not exist.
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    
    plot_all_loss(
        args.log_step, 
        all_loss, 
        plot_dir,
        args.plot_name,
        args.title,
        labels
    )
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Plot')

    # Loss paths
    parser.add_argument('--exp_root', type=str, default='./',
                        help='root of the exp folders')
    parser.add_argument('--exp_type_id', type=int, default=0, 
                        help='type ID of the name of the experiment to load')
    parser.add_argument('--exp_ids', nargs='+', default=[1],
                        help='list of the IDs of the experiments to be loaded')
    
    # Plot settings
    parser.add_argument('--log_step', type=int, default=10)
    parser.add_argument('--label_attr', type=str, help='attribute name of the plot labels')
    parser.add_argument('--label_vals', nargs='+', help='values of the plot labels')
    parser.add_argument('--plot_root', type=str, default='./plots', help='root dir to save the plots')
    parser.add_argument('--plot_name', type=str)
    parser.add_argument('--title', type=str)

    args = parser.parse_args()
    print(args)

    main(args)
    