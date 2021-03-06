import argparse
import os

from click.decorators import password_option
from torch.backends import cudnn

from data_loader import get_loader
from trainer import Trainer


def str2bool(v):
    return v.lower() in ('true')

def main(config):
    # For fast training.
    cudnn.benchmark = True

    # Create directories if not exist.
    if not os.path.exists(config.log_dir):
        os.makedirs(config.log_dir)
    if not os.path.exists(config.model_save_dir):
        os.makedirs(config.model_save_dir)
    if not os.path.exists(config.sample_dir):
        os.makedirs(config.sample_dir)
    if not os.path.exists(config.result_dir):
        os.makedirs(config.result_dir)
    if not os.path.exists(config.config_dir):
        os.makedirs(config.config_dir)
    if not os.path.exists(config.progress_dir):
        os.makedirs(config.progress_dir)
    
    # Save configs to file
    with open(config.config_dir + '/configs.txt', 'w') as file:
        config_dict = vars(config)
        for arg in config_dict:
            file.write("{}: {}\n".format(arg, config_dict[arg]))

    # Data loader.
    celeba_loader = None
    rafd_loader = None
    assert config.dataset == 'CelebA', print("{} dataset is not supported".format(config.dataset))

    celeba_loader = get_loader(config.celeba_image_dir, config.attr_path, config.selected_attrs,
                                config.celeba_crop_size, config.image_size, config.batch_size,
                                'CelebA', config.mode, config.num_workers)

    # Trainer for training and testing StarGAN.
    trainer = Trainer(celeba_loader, rafd_loader, config)

    # Ensure test iter is no greater than train iters
    config.test_iters = min(config.test_iters, config.num_iters)

    if config.mode == 'train':
        trainer.train()
    elif config.mode == 'test':
        trainer.test()
    else:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # Model configuration.
    parser.add_argument('--c_dim', type=int, default=5, help='dimension of domain labels (1st dataset)')
    parser.add_argument('--c2_dim', type=int, default=8, help='dimension of domain labels (2nd dataset)')
    parser.add_argument('--celeba_crop_size', type=int, default=178, help='crop size for the CelebA dataset')
    parser.add_argument('--rafd_crop_size', type=int, default=256, help='crop size for the RaFD dataset')
    parser.add_argument('--image_size', type=int, default=128, help='image resolution')
    parser.add_argument('--g_conv_dim', type=int, default=64, help='number of conv filters in the first layer of G')
    parser.add_argument('--d_conv_dim', type=int, default=64, help='number of conv filters in the first layer of D')
    parser.add_argument('--g_repeat_num', type=int, default=6, help='number of residual blocks in G')
    parser.add_argument('--d_repeat_num', type=int, default=6, help='number of strided conv layers in D')
    parser.add_argument('--lambda_cls', type=float, default=1, help='weight for domain classification loss')
    parser.add_argument('--lambda_rec', type=float, default=10, help='weight for reconstruction loss')
    parser.add_argument('--lambda_gp', type=float, default=10, help='weight for gradient penalty')
    
    # Training configuration.
    parser.add_argument('--dataset', type=str, default='CelebA', choices=['CelebA', 'RaFD', 'Both'])
    parser.add_argument('--batch_size', type=int, default=16, help='mini-batch size')
    parser.add_argument('--num_iters', type=int, default=200000, help='number of total iterations for training D')
    parser.add_argument('--num_iters_decay', type=int, default=100000, help='number of iterations for decaying lr')
    parser.add_argument('--g_lr', type=float, default=0.0001, help='learning rate for G')
    parser.add_argument('--d_lr', type=float, default=0.0001, help='learning rate for D')
    parser.add_argument('--n_critic', type=int, default=5, help='number of D updates per each G update')
    parser.add_argument('--beta1', type=float, default=0.5, help='beta1 for Adam optimizer')
    parser.add_argument('--beta2', type=float, default=0.999, help='beta2 for Adam optimizer')
    parser.add_argument('--resume_iters', type=int, default=None, help='resume training from this step')
    parser.add_argument('--selected_attrs', '--list', nargs='+', help='selected attributes for the CelebA dataset',
                        default=['Black_Hair', 'Blond_Hair', 'Brown_Hair', 'Male', 'Young'])

    # Training configuration for sliced wasserstein loss.
    parser.add_argument("--d_criterion", default='BCE', const='BCE', nargs='?', choices=['BCE', 'WGAN-GP'],
                        help="criterion to train the discriminator when using SWD or max-SWD")

    parser.add_argument('--use_sw_loss', type=str2bool, default=False, help='train using sliced wasserstein loss')
    parser.add_argument('--num_projections', type=int, default=10000, help='num of projections used to compute the swd')
    parser.add_argument('--use_d_feature', type=str2bool, default=False, help='use features of the discriminator to get swd')

    # Training configuration for max sliced wasserstein loss.
    parser.add_argument('--use_max_sw_loss', type=str2bool, default=False, help='train using max sliced wasserstein loss')
    parser.add_argument('--sort_scalar', type=str2bool, default=False, 
                        help='sort scalar output [w^T*h] when computing the max swd; if false, sort vector output [h]') 

    # Test configuration.
    parser.add_argument('--test_iters', type=int, default=100000, help='test model from this step')
    parser.add_argument('--test_type', default='general', const='general', nargs='?', choices=['general', 'small'], 
                        help='type of the test to perform')
    parser.add_argument('--test_img_numbers', nargs='+', default=[10, 165],
                        help='the No. of the selected images for small test')

    # Miscellaneous.
    parser.add_argument('--num_workers', type=int, default=1)
    parser.add_argument('--mode', type=str, default='train', choices=['train', 'test'])
    parser.add_argument('--use_tensorboard', type=str2bool, default=True)
    parser.add_argument('--cuda_device_name', type=str, default='cuda:0', choices=['cuda:0', 'cuda:1', 'cuda:2'])

    # Directories.
    parser.add_argument('--celeba_image_dir', type=str, default='data/celeba/images')
    parser.add_argument('--attr_path', type=str, default='data/celeba/list_attr_celeba.txt')
    parser.add_argument('--rafd_image_dir', type=str, default='data/RaFD/train')
    parser.add_argument('--log_dir', type=str, default='stargan/logs')
    parser.add_argument('--model_save_dir', type=str, default='stargan/models')
    parser.add_argument('--sample_dir', type=str, default='stargan/samples')
    parser.add_argument('--result_dir', type=str, default='stargan/results')
    parser.add_argument('--config_dir', type=str, default='stargan/configs', help="save the configs to file")
    parser.add_argument('--progress_dir', type=str, default='stargan/progress', help="record the training info")

    # Step size.
    parser.add_argument('--log_step', type=int, default=10)
    parser.add_argument('--sample_step', type=int, default=1000)
    parser.add_argument('--model_save_step', type=int, default=10000)
    parser.add_argument('--lr_update_step', type=int, default=1000)

    config = parser.parse_args()

    # Validate the training configs
    assert not (config.use_sw_loss and config.use_max_sw_loss), \
        print("Config use_sw_loss and use_max_sw_loss cannot be True at the same time.")

    print(config)

    # Execute
    main(config)