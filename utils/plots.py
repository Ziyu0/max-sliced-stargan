"""Tools to create plots.

Created on April 20, 2019
Updated on
@author: Ziyu
"""
import matplotlib
matplotlib.use("TkAgg")         # prevent matplotlib from crashing on MacOS
import matplotlib.pyplot as plt

import numpy as np
import argparse
import os

from file_io import load_loss_files

def plot_all_loss(log_step, all_loss, plot_dir, title, labels):
    """Plot all items for the loss of specified experiments.
    Note that only loss of the same type of experiments can be put together.
    Plots will be saved as plot_dir/loss_tag.png
    """

    # Leave the color as default?

    loss_tags = list(all_loss[0].keys())

    # Create a plot for each loss tag
    for loss_tag in loss_tags:
        print("Plotting {}...".format(loss_tag))

        # Create a new figure
        plt.figure()

        # Plot loss for each exp
        for i, loss_dict in enumerate(all_loss):
            x = list( range(0, len(loss_dict[loss_tag]) * log_step, log_step) )
            plt.plot(x, loss_dict[loss_tag], label=labels[i], 
                     alpha=0.6, linewidth=0.6, clip_on=False)
        
            num_iters = len(loss_dict[loss_tag])
        
        # Set x axis, limit to 10 ticks only
        total_num_iters = num_iters * log_step
        inteval = total_num_iters // 10
        x_ticks = list(range(0, total_num_iters + log_step, inteval))

        # Change labels of x_ticks to ['0', '20k', '40k', ...]
        x_tick_labels = [str(num // 1000) + 'k' for num in x_ticks]
        x_tick_labels[0] = '0'
        
        # Configure the plot info
        plt.xticks(x_ticks, labels=x_tick_labels)
        plt.xlabel('Iterations')
        plt.ylabel('Training loss [{}]'.format(loss_tag))
        plt.legend(loc='upper right')
        plt.title(title)

        # Convert loss_tag 'D/loss_real' => 'D_loss_real' and save
        save_path = '{}/{}.png'.format(plot_dir, '_'.join(loss_tag.split('/')))
        plt.savefig(save_path, format='png', dpi=150)
        print('Figure saved as', save_path)

        # Clear the current figure
        plt.close()

def plot_g_fake_loss():
    """Plot only G/loss_fake for the loss of specified experiments."""
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
    print("==> Loading loss...")
    all_loss = load_loss_files(args.exp_root, exp_name, exp_ids)

    # Create labels for the plot, such as 'n_critic = 5'
    labels = []
    for val in args.label_vals:
        labels.append('{} = {}'.format(args.label_attr, val))
    
    # Get subdir to save the plots, eg, 'plots/stargan_celeba[n_critic]'
    plot_dir = '{}/{}_[{}]'.format(args.plot_root, exp_name, args.label_attr)
    # Create directories if not exist.
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)
    
    print("==> Generating plots...")
    plot_all_loss(
        args.log_step, 
        all_loss, 
        plot_dir,
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
    parser.add_argument('--title', type=str)

    args = parser.parse_args()
    print(args)

    main(args)
    