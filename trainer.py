import datetime
import os
import time

import numpy as np
import torch
import torch.nn.functional as F
from torch.autograd import Variable
from torchvision.utils import save_image

from model import Discriminator, Generator
from swd import sliced_wasserstein_distance


class Trainer(object):
    """Trainer for training and testing StarGAN."""

    def __init__(self, celeba_loader, rafd_loader, config):
        """Initialize configurations."""

        # Data loader.
        self.celeba_loader = celeba_loader
        self.rafd_loader = rafd_loader

        # Model configurations.
        self.c_dim = config.c_dim
        self.c2_dim = config.c2_dim
        self.image_size = config.image_size
        self.g_conv_dim = config.g_conv_dim
        self.d_conv_dim = config.d_conv_dim
        self.g_repeat_num = config.g_repeat_num
        self.d_repeat_num = config.d_repeat_num
        self.lambda_cls = config.lambda_cls
        self.lambda_rec = config.lambda_rec
        self.lambda_gp = config.lambda_gp

        # Training configurations.
        self.dataset = config.dataset
        self.batch_size = config.batch_size
        self.num_iters = config.num_iters
        self.num_iters_decay = config.num_iters_decay
        self.g_lr = config.g_lr
        self.d_lr = config.d_lr
        self.n_critic = config.n_critic
        self.beta1 = config.beta1
        self.beta2 = config.beta2
        self.resume_iters = config.resume_iters
        self.selected_attrs = config.selected_attrs

        # TODO: add the configs here
        # Training configuration for sliced wasserstein loss.
        self.d_criterion = config.d_criterion
        self.use_sw_loss = config.use_sw_loss
        self.num_projections = config.num_projections if self.use_sw_loss else 0
        self.use_d_feature = config.use_d_feature

        # Training configuration for max sliced wasserstein loss.
        self.use_max_sw_loss = config.use_max_sw_loss

        # Test configurations.
        self.test_iters = config.test_iters

        # Miscellaneous.
        self.use_tensorboard = config.use_tensorboard
        if torch.cuda.is_available():
            device_name = config.cuda_device_name if config.cuda_device_name else 'cuda'
            self.device = torch.device(device_name)
        else:
            self.device = torch.device('cpu')
        # self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print("Init solver on device {}".format(self.device))

        # Directories.
        self.log_dir = config.log_dir
        self.sample_dir = config.sample_dir
        self.model_save_dir = config.model_save_dir
        self.result_dir = config.result_dir
        self.progress_dir = config.progress_dir

        # Step size.
        self.log_step = config.log_step
        self.sample_step = config.sample_step
        self.model_save_step = config.model_save_step
        self.lr_update_step = config.lr_update_step

        # Build the model and tensorboard.
        self.build_model()
        if self.use_tensorboard:
            self.build_tensorboard()
        
        # Build event logger.
        self.build_event_logger()

    def build_model(self):
        """Create a generator and a discriminator."""
        use_d_feature_flag = (self.use_sw_loss and self.use_d_feature) or self.use_max_sw_loss

        if self.dataset in ['CelebA', 'RaFD']:
            self.G = Generator(self.g_conv_dim, self.c_dim, self.g_repeat_num)
            self.D = Discriminator(self.image_size, self.d_conv_dim, self.c_dim, self.d_repeat_num,
                                   use_d_feature=use_d_feature_flag) 
        elif self.dataset in ['Both']:
            self.G = Generator(self.g_conv_dim, self.c_dim+self.c2_dim+2, self.g_repeat_num)   # 2 for mask vector.
            self.D = Discriminator(self.image_size, self.d_conv_dim, self.c_dim+self.c2_dim, self.d_repeat_num,
                                   use_d_feature=use_d_feature_flag)

        self.g_optimizer = torch.optim.Adam(self.G.parameters(), self.g_lr, [self.beta1, self.beta2])
        self.d_optimizer = torch.optim.Adam(self.D.parameters(), self.d_lr, [self.beta1, self.beta2])
        self.print_network(self.G, 'G')
        self.print_network(self.D, 'D')
        
        self.G.to(self.device)
        self.D.to(self.device)

    def print_network(self, model, name):
        """Print out the network information."""
        num_params = 0
        for p in model.parameters():
            num_params += p.numel()
        print(model)
        print(name)
        print("The number of parameters: {}".format(num_params))

    def restore_model(self, resume_iters):
        """Restore the trained generator and discriminator."""
        print('Loading the trained models from step {}...'.format(resume_iters))
        G_path = os.path.join(self.model_save_dir, '{}-G.ckpt'.format(resume_iters))
        D_path = os.path.join(self.model_save_dir, '{}-D.ckpt'.format(resume_iters))
        self.G.load_state_dict(torch.load(G_path, map_location=lambda storage, loc: storage))
        self.D.load_state_dict(torch.load(D_path, map_location=lambda storage, loc: storage))

    def build_tensorboard(self):
        """Build a tensorboard logger."""
        from logger import Logger
        self.logger = Logger(self.log_dir)
    
    def build_event_logger(self):
        """Build an event logger."""
        from logger import EventLogger
        event_path = self.progress_dir + "/progress.log"
        self.event_logger = EventLogger('training', event_path)

    def update_lr(self, g_lr, d_lr):
        """Decay learning rates of the generator and discriminator."""
        for param_group in self.g_optimizer.param_groups:
            param_group['lr'] = g_lr
        for param_group in self.d_optimizer.param_groups:
            param_group['lr'] = d_lr

    def reset_grad(self):
        """Reset the gradient buffers."""
        self.g_optimizer.zero_grad()
        self.d_optimizer.zero_grad()

    def denorm(self, x):
        """Convert the range from [-1, 1] to [0, 1]."""
        out = (x + 1) / 2
        return out.clamp_(0, 1)

    def gradient_penalty(self, y, x):
        """Compute gradient penalty: (L2_norm(dy/dx) - 1)**2."""
        weight = torch.ones(y.size()).to(self.device)
        dydx = torch.autograd.grad(outputs=y,
                                   inputs=x,
                                   grad_outputs=weight,
                                   retain_graph=True,
                                   create_graph=True,
                                   only_inputs=True)[0]

        dydx = dydx.view(dydx.size(0), -1)
        dydx_l2norm = torch.sqrt(torch.sum(dydx**2, dim=1))
        return torch.mean((dydx_l2norm-1)**2)

    def label2onehot(self, labels, dim):
        """Convert label indices to one-hot vectors."""
        batch_size = labels.size(0)
        out = torch.zeros(batch_size, dim)
        out[np.arange(batch_size), labels.long()] = 1
        return out

    def create_labels(self, c_org, c_dim=5, dataset='CelebA', selected_attrs=None):
        """Generate target domain labels for debugging and testing."""
        # Get hair color indices.
        if dataset == 'CelebA':
            hair_color_indices = []
            for i, attr_name in enumerate(selected_attrs):
                if attr_name in ['Black_Hair', 'Blond_Hair', 'Brown_Hair', 'Gray_Hair']:
                    hair_color_indices.append(i)

        c_trg_list = []
        for i in range(c_dim):
            if dataset == 'CelebA':
                c_trg = c_org.clone()
                if i in hair_color_indices:  # Set one hair color to 1 and the rest to 0.
                    c_trg[:, i] = 1
                    for j in hair_color_indices:
                        if j != i:
                            c_trg[:, j] = 0
                else:
                    c_trg[:, i] = (c_trg[:, i] == 0)  # Reverse attribute value.
            elif dataset == 'RaFD':
                c_trg = self.label2onehot(torch.ones(c_org.size(0))*i, c_dim)

            c_trg_list.append(c_trg.to(self.device))
        return c_trg_list

    def classification_loss(self, logit, target, dataset='CelebA'):
        """Compute binary or softmax cross entropy loss.
        
        Args:
            logits: Vector of classification probabilities, shape (N, c_dim)
            target: Vector of true mask labels, shape (N, c_dim)
        """
        if dataset == 'CelebA':
            return F.binary_cross_entropy_with_logits(logit, target, size_average=False) / logit.size(0)
        elif dataset == 'RaFD':
            return F.cross_entropy(logit, target)

    def log_training_info(self, et, loss, step):
        """Helper function for training - Print out training information and 
        save the info to file. Add summary to tensorboard if enabled.

        Args:
            et: Elasped time of the current training step from the start time
            loss(dict): Dictionary containing loss of the generator and discriminator
            step(int): Currrent iteration step
        """
        et = str(datetime.timedelta(seconds=et))[:-7]
        info = "Elapsed [{}], Iteration [{}/{}]".format(et, step+1, self.num_iters)
        for tag, value in loss.items():
            info += ", {}: {:.4f}".format(tag, value)

        self.event_logger.log(info)

        if self.use_tensorboard:
            for tag, value in loss.items():
                self.logger.scalar_summary(tag, value, step+1)

    def translate_samples(self, step, x_fixed, c_fixed_list):
        """Helper function for training - Translate fixed images for debugging.

        Args:
            step(int): Currrent iteration step
            x_fixed(tensor): Real images, shape (N, C, H, W)
            c_fixed_list(list<tensor>): Target labels, each item's shape = (N, c_dim)
        """
        with torch.no_grad():            
            # Control the number of sampled used
            limit = x_fixed.size(0) if x_fixed.size(0) < 16 else 16

            x_fixed = x_fixed[:limit, :, :, :]
            x_fake_list = [x_fixed]
            for c_fixed in c_fixed_list:
                x_fake_list.append(self.G(x_fixed, c_fixed[:limit, :]))
            
            x_concat = torch.cat(x_fake_list, dim=3)
            sample_path = os.path.join(self.sample_dir, '{}-images.jpg'.format(step + 1))
            save_image(self.denorm(x_concat.data.cpu()), sample_path, nrow=1, padding=0)
            info = 'Saved real and fake images into {}...'.format(sample_path)
            self.event_logger.log(info)
    
    def translate_samples_multi(self, step, x_fixed, c_celeba_list, c_rafd_list,
                                zero_rafd, zero_celeba, mask_celeba, mask_rafd):
        """Helper function for training - Translate fixed images for debugging.
        
        Args:
            step(int): Currrent iteration step
            x_fixed(tensor): Real images, shape (N, C, H, W)
            c_celeba_list, c_rafd_list(list<tensor>): Target labels, each item's shape = (N, c_dim)
            zero_rafd, zero_celeba(tensor): shape (N, c_dim)
            mask_celeba, mask_rafd(tensor): shape (N, c_dim)
        """
        with torch.no_grad():
            # Control the number of sampled used
            limit = x_fixed.size(0) if x_fixed.size(0) < 16 else 16

            x_fixed = x_fixed[:limit, :, :, :]
            x_fake_list = [x_fixed]
            for c_fixed in c_celeba_list:
                c_trg = torch.cat(
                    [c_fixed[:limit, :], zero_rafd[:limit, :], mask_celeba[:limit, :]], 
                    dim=1
                )
                x_fake_list.append(self.G(x_fixed, c_trg))
            for c_fixed in c_rafd_list:
                c_trg = torch.cat(
                    [zero_celeba[:limit, :], c_fixed[:limit, :], mask_rafd[:limit, :]], 
                    dim=1
                )
                x_fake_list.append(self.G(x_fixed, c_trg))
            
            x_concat = torch.cat(x_fake_list, dim=3)
            sample_path = os.path.join(self.sample_dir, '{}-images.jpg'.format(step + 1))
            save_image(self.denorm(x_concat.data.cpu()), sample_path, nrow=1, padding=0)
            info = 'Saved real and fake images into {}...'.format(sample_path)
            self.event_logger.log(info)
    
    def save_checkpoints(self, step):
        """Helper function for training - Save model checkpoints."""
        G_path = os.path.join(self.model_save_dir, '{}-G.ckpt'.format(step + 1))
        D_path = os.path.join(self.model_save_dir, '{}-D.ckpt'.format(step + 1))
        torch.save(self.G.state_dict(), G_path)
        torch.save(self.D.state_dict(), D_path)
        info = 'Saved model checkpoints into {}...'.format(self.model_save_dir)
        self.event_logger.log(info)
    
    def decay_learning_rates(self, g_lr, d_lr):
        """Helper function for training - Decay learning rates."""
        g_lr -= (self.g_lr / float(self.num_iters_decay))
        d_lr -= (self.d_lr / float(self.num_iters_decay))
        self.update_lr(g_lr, d_lr)
        info = 'Decayed learning rates, g_lr: {}, d_lr: {}.'.format(g_lr, d_lr)
        self.event_logger.log(info)

        return g_lr, d_lr

    def _train_D_wasserstein_GP(self, data):
        """[For original StarGAN objective or SWD and max-SWD] 
        Train discriminator using wasserstein distance with gradient penalty.
        
        Args:
            data(dict): Dict containing image and label data, namely:
                x_real(tensor): Input images
                c_org(tensor):
                c_trg(tensor): Target domain labels
                label_org(tensor): Labels for computing classification loss
                label_trg(tensor): Labels for computing classification loss
        Returns:
            loss(dict): Dict containing loss of the current step for tensorboard logging
        """

        # Unpack the data
        x_real = data['x_real']
        c_trg = data['c_trg']
        label_org = data['label_org']

        # Compute loss with real images.
        outputs = self.D(x_real)        # len will be either 2 or 3
        out_src, out_cls = outputs[0], outputs[1]

        d_loss_real = - torch.mean(out_src)
        d_loss_cls = self.classification_loss(out_cls, label_org, self.dataset)

        # Compute loss with fake images.
        x_fake = self.G(x_real, c_trg)
        outputs = self.D(x_fake.detach())
        out_src, out_cls = outputs[0], outputs[1]
        
        d_loss_fake = torch.mean(out_src)

        # Compute loss for gradient penalty.
        alpha = torch.rand(x_real.size(0), 1, 1, 1).to(self.device)
        x_hat = (alpha * x_real.data + (1 - alpha) * x_fake.data).requires_grad_(True)
        out_src, _ = self.D(x_hat)
        d_loss_gp = self.gradient_penalty(out_src, x_hat)

        # Backward and optimize.
        d_loss = d_loss_real + d_loss_fake + self.lambda_cls * d_loss_cls + self.lambda_gp * d_loss_gp
        self.reset_grad()
        d_loss.backward()
        self.d_optimizer.step()

        # Logging.
        loss = {}
        loss['D/loss_real'] = d_loss_real.item()
        loss['D/loss_fake'] = d_loss_fake.item()
        loss['D/loss_cls'] = d_loss_cls.item()
        loss['D/loss_gp'] = d_loss_gp.item()

        return loss
    
    def _train_G_wasserstein(self, data):
        """[For original StarGAN objective] 
        Train generator using wasserstein distance (along with discriminator's wasserstein
        distance with gradient penalty to form the WGAN-GP objective).
        """

        # Unpack the data
        x_real = data['x_real']
        c_org = data['c_org']
        c_trg = data['c_trg']
        label_trg = data['label_trg']

        # Original-to-target domain.
        x_fake = self.G(x_real, c_trg)
        out_src, out_cls = self.D(x_fake)
        g_loss_fake = - torch.mean(out_src)
        g_loss_cls = self.classification_loss(out_cls, label_trg, self.dataset)

        # Target-to-original domain.
        x_reconst = self.G(x_fake, c_org)
        g_loss_rec = torch.mean(torch.abs(x_real - x_reconst))

        # Backward and optimize.
        g_loss = g_loss_fake + self.lambda_rec * g_loss_rec + self.lambda_cls * g_loss_cls
        self.reset_grad()
        g_loss.backward()
        self.g_optimizer.step()

        # Logging.
        loss = {}
        loss['G/loss_fake'] = g_loss_fake.item()
        loss['G/loss_rec'] = g_loss_rec.item()
        loss['G/loss_cls'] = g_loss_cls.item()
        
        return loss
    
    def _train_D_BCE(self, data):
        """[For SWD or max-SWD]
        Train discriminator using binary cross entropy loss. The discriminator will output 
        additional features along with the out_src and out_cls if use_d_feature is enbaled.
        """
        # Unpack the data
        x_real = data['x_real']
        c_trg = data['c_trg']
        label_org = data['label_org']
        
        # Compute loss with real images
        outputs = self.D(x_real)
        assert (len(outputs) == 3 and self.use_d_feature) or (len(outputs) == 2 and not self.use_d_feature)
        
        out_src, out_cls = outputs[0], outputs[1]
        d_loss_real = F.binary_cross_entropy_with_logits(out_src, torch.ones_like(out_src))
        d_loss_cls = self.classification_loss(out_cls, label_org, self.dataset)

        # Compute loss with fake images
        x_fake = self.G(x_real, c_trg)
        outputs = self.D(x_fake.detach())
        assert (len(outputs) == 3 and self.use_d_feature) or (len(outputs) == 2 and not self.use_d_feature)
        out_src, out_cls = outputs[0], outputs[1]

        d_loss_fake = F.binary_cross_entropy_with_logits(out_src, torch.zeros_like(out_src))

        # Backward and optimize.
        d_loss = d_loss_real + d_loss_fake + self.lambda_cls * d_loss_cls
        self.reset_grad()
        d_loss.backward()
        self.d_optimizer.step()

        # Logging.
        loss = {}
        loss['D/loss_real'] = d_loss_real.item()
        loss['D/loss_fake'] = d_loss_fake.item()
        loss['D/loss_cls'] = d_loss_cls.item()

        return loss
    
    def _train_G_sliced_wasserstein(self, data):
        """[For SWD]
        Train generator using sliced wasserstein distance (along with discriminator's BCE loss
        to form the objective). The discriminator will output additional features along with the 
        out_src and out_cls if use_d_feature is enbaled
        """

        # Unpack the data
        x_real = data['x_real']
        c_org = data['c_org']
        c_trg = data['c_trg']
        label_trg = data['label_trg']
        
        # Original-to-target domain
        x_fake = self.G(x_real, c_trg)
        num_samples = x_real.shape[0]

        outputs = self.D(x_fake)

        if self.use_d_feature:
            assert len(outputs) == 3
            out_src, out_cls, h_fake = outputs
            _, _, h_real = self.D(x_real)

            g_loss_fake = sliced_wasserstein_distance(
                h_real.view(num_samples, -1), h_fake.view(num_samples, -1),
                self.num_projections, self.device
            )
        else:
            assert len(outputs) == 2
            out_src, out_cls = outputs
            g_loss_fake = sliced_wasserstein_distance(
                x_real.view(num_samples, -1), x_fake.view(num_samples, -1),
                self.num_projections, self.device
            )
        
        g_loss_cls = self.classification_loss(out_cls, label_trg, self.dataset)
        
        # Target-to-original domain.
        x_reconst = self.G(x_fake, c_org)
        g_loss_rec = torch.mean(torch.abs(x_real - x_reconst))

        # Backward and optimize.
        g_loss = g_loss_fake + self.lambda_rec * g_loss_rec + self.lambda_cls * g_loss_cls
        self.reset_grad()
        g_loss.backward()
        self.g_optimizer.step()

        # Logging.
        loss = {}
        loss['G/loss_fake'] = g_loss_fake.item()
        loss['G/loss_rec'] = g_loss_rec.item()
        loss['G/loss_cls'] = g_loss_cls.item()

        return loss
    
    def _train_G_max_sliced_wasserstein(self, data):
        """[For max-SWD]
        Train generator using max sliced wasserstein distance."""
        
        # Unpack the data
        x_real = data['x_real']
        c_org = data['c_org']
        c_trg = data['c_trg']
        label_trg = data['label_trg']

        # TODO: Finish this

    def load_training_method(self):
        """Load the correct methods to train the discriminator and generator based on the 
        training configs use_sw_loss and use_max_sw_loss. If both are set to false, then
        the original method of the StarGAN paper will be loaded.
        
        Returns:
            methods(dict): Dict containing functions to train D and G
        """

        original, swd, max_swd = 'original', 'SWD', 'max-SWD'
        
        # Using BCE or WGAN-GP for the discriminator to assist SWD or max-SWD
        d_method_for_swd = {
            'BCE': self._train_D_BCE,
            'WGAN-GP': self._train_D_wasserstein_GP
        }

        d_method = {
            original: self._train_D_wasserstein_GP,
            swd: d_method_for_swd[self.d_criterion],
            max_swd: d_method_for_swd[self.d_criterion]
        }
        g_method = {
            original: self._train_G_wasserstein,
            swd: self._train_G_sliced_wasserstein,
            max_swd: self._train_G_max_sliced_wasserstein
        }

        # Choose the correct method to train D and G
        if self.use_sw_loss:
            d_method_name = g_method_name = swd
        elif self.use_max_sw_loss:
            d_method_name = g_method_name = max_swd
        else:
            d_method_name = g_method_name = original

        methods = {
            'train_D': d_method[d_method_name],
            'train_G': g_method[g_method_name]
        }

        return methods
        

    def train(self):
        """Train StarGAN within a single dataset."""
        # Set data loader.
        if self.dataset == 'CelebA':
            data_loader = self.celeba_loader
        elif self.dataset == 'RaFD':
            data_loader = self.rafd_loader

        # Fetch fixed inputs for debugging.
        data_iter = iter(data_loader)
        x_fixed, c_org = next(data_iter)
        x_fixed = x_fixed.to(self.device)
        c_fixed_list = self.create_labels(c_org, self.c_dim, self.dataset, self.selected_attrs)

        # Learning rate cache for decaying.
        g_lr = self.g_lr
        d_lr = self.d_lr

        # Start training from scratch or resume training.
        start_iters = 0
        if self.resume_iters:
            start_iters = self.resume_iters
            self.restore_model(self.resume_iters)
        
        # Load the correct training method
        methods = self.load_training_method()
        for key in methods:
            print("{} method: {}".format(key, methods[key].__name__))

        # Start training.
        print('Start training...')
        start_time = time.time()

        for i in range(start_iters, self.num_iters):

            # =========================== 1. Preprocess input data ============================== #

            # Fetch real images and labels.
            try:
                x_real, label_org = next(data_iter)
            except:
                data_iter = iter(data_loader)
                x_real, label_org = next(data_iter)

            # Generate target domain labels randomly.
            rand_idx = torch.randperm(label_org.size(0))
            label_trg = label_org[rand_idx]

            if self.dataset == 'CelebA':
                c_org = label_org.clone()
                c_trg = label_trg.clone()
            elif self.dataset == 'RaFD':
                c_org = self.label2onehot(label_org, self.c_dim)
                c_trg = self.label2onehot(label_trg, self.c_dim)

            x_real = x_real.to(self.device)           # Input images.
            c_org = c_org.to(self.device)             # Original domain labels.
            c_trg = c_trg.to(self.device)             # Target domain labels.
            label_org = label_org.to(self.device)     # Labels for computing classification loss.
            label_trg = label_trg.to(self.device)     # Labels for computing classification loss.

            # Pack the data for the training methods
            data = {
                'x_real': x_real,
                'c_org': c_org,
                'c_trg': c_trg,
                'label_org': label_org,
                'label_trg': label_trg
            }

            # =================================== 2. Training =================================== #

            # For logging the loss.
            loss = {}

            # Train the discriminator
            d_loss = methods['train_D'](data)
            loss.update(d_loss)

            # Train the generator 
            if (i + 1) % self.n_critic == 0:
                g_loss = methods['train_G'](data)
                loss.update(g_loss)

            # =============================== 3. Miscellaneous ================================== #

            # Print out training information.
            if (i + 1) % self.log_step == 0:
                et = time.time() - start_time  ### Pass this et to log_training_info
                self.log_training_info(et, loss, i)

            # Translate fixed images for debugging.
            if (i + 1) % self.sample_step == 0:
                self.translate_samples(i, x_fixed, c_fixed_list)

            # Save model checkpoints.
            if (i + 1) % self.model_save_step == 0 or (i+1) == self.num_iters:
                self.save_checkpoints(i)

            # Decay learning rates.
            if (i + 1) % self.lr_update_step == 0 and (i+1) > (self.num_iters - self.num_iters_decay):
                g_lr, d_lr = self.decay_learning_rates(g_lr, d_lr)


    # def train(self):
    #     """Train StarGAN within a single dataset."""
    #     # Set data loader.
    #     if self.dataset == 'CelebA':
    #         data_loader = self.celeba_loader
    #     elif self.dataset == 'RaFD':
    #         data_loader = self.rafd_loader

    #     # Fetch fixed inputs for debugging.
    #     data_iter = iter(data_loader)
    #     x_fixed, c_org = next(data_iter)
    #     x_fixed = x_fixed.to(self.device)
    #     c_fixed_list = self.create_labels(c_org, self.c_dim, self.dataset, self.selected_attrs)

    #     # Learning rate cache for decaying.
    #     g_lr = self.g_lr
    #     d_lr = self.d_lr

    #     # Start training from scratch or resume training.
    #     start_iters = 0
    #     if self.resume_iters:
    #         start_iters = self.resume_iters
    #         self.restore_model(self.resume_iters)

    #     # Start training.
    #     print('Start training...')
    #     start_time = time.time()
    #     for i in range(start_iters, self.num_iters):

    #         # =================================================================================== #
    #         #                             1. Preprocess input data                                #
    #         # =================================================================================== #

    #         # Fetch real images and labels.
    #         try:
    #             x_real, label_org = next(data_iter)
    #         except:
    #             data_iter = iter(data_loader)
    #             x_real, label_org = next(data_iter)

    #         # Generate target domain labels randomly.
    #         rand_idx = torch.randperm(label_org.size(0))
    #         label_trg = label_org[rand_idx]

    #         if self.dataset == 'CelebA':
    #             c_org = label_org.clone()
    #             c_trg = label_trg.clone()
    #         elif self.dataset == 'RaFD':
    #             c_org = self.label2onehot(label_org, self.c_dim)
    #             c_trg = self.label2onehot(label_trg, self.c_dim)

    #         x_real = x_real.to(self.device)           # Input images.
    #         c_org = c_org.to(self.device)             # Original domain labels.
    #         c_trg = c_trg.to(self.device)             # Target domain labels.
    #         label_org = label_org.to(self.device)     # Labels for computing classification loss.
    #         label_trg = label_trg.to(self.device)     # Labels for computing classification loss.

    #         # =================================================================================== #
    #         #                             2. Train the discriminator                              #
    #         # =================================================================================== #

    #         # Compute loss with real images.
    #         out_src, out_cls = self.D(x_real)
    #         d_loss_real = - torch.mean(out_src)
    #         d_loss_cls = self.classification_loss(out_cls, label_org, self.dataset)

    #         # Compute loss with fake images.
    #         x_fake = self.G(x_real, c_trg)
    #         out_src, out_cls = self.D(x_fake.detach())
    #         d_loss_fake = torch.mean(out_src)

    #         # Compute loss for gradient penalty.
    #         alpha = torch.rand(x_real.size(0), 1, 1, 1).to(self.device)
    #         x_hat = (alpha * x_real.data + (1 - alpha) * x_fake.data).requires_grad_(True)
    #         out_src, _ = self.D(x_hat)
    #         d_loss_gp = self.gradient_penalty(out_src, x_hat)

    #         # Backward and optimize.
    #         d_loss = d_loss_real + d_loss_fake + self.lambda_cls * d_loss_cls + self.lambda_gp * d_loss_gp
    #         self.reset_grad()
    #         d_loss.backward()
    #         self.d_optimizer.step()

    #         # Logging.
    #         loss = {}
    #         loss['D/loss_real'] = d_loss_real.item()
    #         loss['D/loss_fake'] = d_loss_fake.item()
    #         loss['D/loss_cls'] = d_loss_cls.item()
    #         loss['D/loss_gp'] = d_loss_gp.item()
            
    #         # =================================================================================== #
    #         #                               3. Train the generator                                #
    #         # =================================================================================== #
            
    #         if (i+1) % self.n_critic == 0:
    #             # Original-to-target domain.
    #             x_fake = self.G(x_real, c_trg)
    #             out_src, out_cls = self.D(x_fake)
    #             g_loss_fake = - torch.mean(out_src)
    #             g_loss_cls = self.classification_loss(out_cls, label_trg, self.dataset)

    #             # Target-to-original domain.
    #             x_reconst = self.G(x_fake, c_org)
    #             g_loss_rec = torch.mean(torch.abs(x_real - x_reconst))

    #             # Backward and optimize.
    #             g_loss = g_loss_fake + self.lambda_rec * g_loss_rec + self.lambda_cls * g_loss_cls
    #             self.reset_grad()
    #             g_loss.backward()
    #             self.g_optimizer.step()

    #             # Logging.
    #             loss['G/loss_fake'] = g_loss_fake.item()
    #             loss['G/loss_rec'] = g_loss_rec.item()
    #             loss['G/loss_cls'] = g_loss_cls.item()

    #         # =================================================================================== #
    #         #                                 4. Miscellaneous                                    #
    #         # =================================================================================== #

    #         # Print out training information.
    #         if (i+1) % self.log_step == 0:
    #             et = time.time() - start_time  ### Pass this et to log_training_info
    #             self.log_training_info(et, loss, i)

    #         # Translate fixed images for debugging.
    #         if (i+1) % self.sample_step == 0:
    #             self.translate_samples(i, x_fixed, c_fixed_list)

    #         # Save model checkpoints.
    #         if (i+1) % self.model_save_step == 0 or (i+1) == self.num_iters:
    #             self.save_checkpoints(i)

    #         # Decay learning rates.
    #         if (i+1) % self.lr_update_step == 0 and (i+1) > (self.num_iters - self.num_iters_decay):
    #             g_lr, d_lr = self.decay_learning_rates(g_lr, d_lr)

    # def train_sw_loss(self):
    #     """Train StarGAN within a single dataset using Sliced Wasserstein Distance."""
    #     # Set data loader.
    #     if self.dataset == 'CelebA':
    #         data_loader = self.celeba_loader
    #     elif self.dataset == 'RaFD':
    #         data_loader = self.rafd_loader

    #     # Fetch fixed inputs for debugging.
    #     data_iter = iter(data_loader)
    #     x_fixed, c_org = next(data_iter)
    #     x_fixed = x_fixed.to(self.device)
    #     c_fixed_list = self.create_labels(c_org, self.c_dim, self.dataset, self.selected_attrs)

    #     # Learning rate cache for decaying.
    #     g_lr = self.g_lr
    #     d_lr = self.d_lr

    #     # Start training from scratch or resume training.
    #     start_iters = 0
    #     if self.resume_iters:
    #         start_iters = self.resume_iters
    #         self.restore_model(self.resume_iters)

    #     # Start training.
    #     print('Start training using SWD on {} dataset...'.format(self.dataset))
    #     start_time = time.time()
    #     for i in range(start_iters, self.num_iters):

    #         # =================================================================================== #
    #         #                             1. Preprocess input data                                #
    #         # =================================================================================== #

    #         # Fetch real images and labels.
    #         try:
    #             x_real, label_org = next(data_iter)
    #         except:
    #             data_iter = iter(data_loader)
    #             x_real, label_org = next(data_iter)

    #         # Generate target domain labels randomly.
    #         rand_idx = torch.randperm(label_org.size(0))
    #         label_trg = label_org[rand_idx]

    #         if self.dataset == 'CelebA':
    #             c_org = label_org.clone()
    #             c_trg = label_trg.clone()
    #         elif self.dataset == 'RaFD':
    #             c_org = self.label2onehot(label_org, self.c_dim)
    #             c_trg = self.label2onehot(label_trg, self.c_dim)

    #         x_real = x_real.to(self.device)           # Input images.
    #         c_org = c_org.to(self.device)             # Original domain labels.
    #         c_trg = c_trg.to(self.device)             # Target domain labels.
    #         label_org = label_org.to(self.device)     # Labels for computing classification loss.
    #         label_trg = label_trg.to(self.device)     # Labels for computing classification loss.

    #         # =================================================================================== #
    #         #                             2. Train the discriminator                              #
    #         # =================================================================================== #
            
    #         # TODO: add a return value of the features for self.D everytime we use it

    #         # Compute loss with real images (use Cross Entropy instead of Wasserstein-GP).
    #         if self.use_d_feature:
    #             out_src, out_cls, _ = self.D(x_real)
    #         else:
    #             out_src, out_cls = self.D(x_real)

    #         # TODO: Do I need to change this?
    #         d_loss_real = F.binary_cross_entropy_with_logits(out_src, torch.ones_like(out_src))

    #         d_loss_cls = self.classification_loss(out_cls, label_org, self.dataset)

    #         # Compute loss with fake images (use Cross Entropy instead of Wasserstein-GP).
    #         x_fake = self.G(x_real, c_trg)

    #         if self.use_d_feature:
    #             out_src, out_cls, _ = self.D(x_fake.detach())  # detach to avoid training G on these labels
    #         else:
    #             out_src, out_cls = self.D(x_fake.detach())

    #         d_loss_fake = F.binary_cross_entropy_with_logits(out_src, torch.zeros_like(out_src))

    #         # Backward and optimize.
    #         d_loss = d_loss_real + d_loss_fake + self.lambda_cls * d_loss_cls
    #         self.reset_grad()
    #         d_loss.backward()
    #         self.d_optimizer.step()

    #         # Logging.
    #         loss = {}
    #         loss['D/loss_real'] = d_loss_real.item()
    #         loss['D/loss_fake'] = d_loss_fake.item()
    #         loss['D/loss_cls'] = d_loss_cls.item()
    #         # loss['D/loss_gp'] = d_loss_gp.item()
            
    #         # =================================================================================== #
    #         #                               3. Train the generator                                #
    #         # =================================================================================== #
            
    #         if (i+1) % self.n_critic == 0:
    #             # Original-to-target domain (use SWD instead of pure Wasserstein).
    #             x_fake = self.G(x_real, c_trg)
    #             num_samples = x_real.shape[0]

    #             # if use discriminator with swd, need to:
    #             # x_real -> D -> x_real_feature -> pass to swd
    #             # x_fake -> D -> x_fake_feature -> pass to swd
    #             # Transform samples using D if enabled
    #             if self.use_d_feature:
    #                 out_src, out_cls, h_fake = self.D(x_fake)
    #                 # torch.Size([128, 1, 1, 1]) torch.Size([128, 3]) torch.Size([128, 2048, 1, 1])
    #                 # print(out_src.shape, out_cls.shape, h_fake.shape)
    #                 _, _, h_real = self.D(x_real)
    #             else:
    #                 out_src, out_cls = self.D(x_fake)

    #             if self.use_d_feature:
    #                 g_loss_fake = sliced_wasserstein_distance(
    #                     h_real.view(num_samples, -1), h_fake.view(num_samples, -1),
    #                     self.num_projections, self.device
    #                 )
    #             else:
    #                 g_loss_fake = sliced_wasserstein_distance(
    #                     x_real.view(num_samples, -1), x_fake.view(num_samples, -1),
    #                     self.num_projections, self.device
    #                 )

    #             g_loss_cls = self.classification_loss(out_cls, label_trg, self.dataset)

    #             # Target-to-original domain.
    #             x_reconst = self.G(x_fake, c_org)
    #             g_loss_rec = torch.mean(torch.abs(x_real - x_reconst))

    #             # Backward and optimize.
    #             g_loss = g_loss_fake + self.lambda_rec * g_loss_rec + self.lambda_cls * g_loss_cls
    #             self.reset_grad()
    #             g_loss.backward()
    #             self.g_optimizer.step()

    #             # Logging.
    #             loss['G/loss_fake'] = g_loss_fake.item()
    #             loss['G/loss_rec'] = g_loss_rec.item()
    #             loss['G/loss_cls'] = g_loss_cls.item()

    #         # =================================================================================== #
    #         #                                 4. Miscellaneous                                    #
    #         # =================================================================================== #

    #         # Print out training information.
    #         if (i+1) % self.log_step == 0:
    #             et = time.time() - start_time  ### Pass this et to log_training_info
    #             self.log_training_info(et, loss, i)

    #         # Translate fixed images for debugging.
    #         if (i+1) % self.sample_step == 0:
    #             self.translate_samples(i, x_fixed, c_fixed_list)

    #         # Save model checkpoints.
    #         if (i+1) % self.model_save_step == 0 or (i+1) == self.num_iters:
    #             self.save_checkpoints(i)
            
    #         # Decay learning rates.
    #         if (i+1) % self.lr_update_step == 0 and (i+1) > (self.num_iters - self.num_iters_decay):
    #             g_lr, d_lr = self.decay_learning_rates(g_lr, d_lr)

    def train_multi(self):
        """Train StarGAN with multiple datasets."""        
        # Data iterators.
        celeba_iter = iter(self.celeba_loader)
        rafd_iter = iter(self.rafd_loader)

        # Fetch fixed inputs for debugging.
        x_fixed, c_org = next(celeba_iter)
        x_fixed = x_fixed.to(self.device)
        c_celeba_list = self.create_labels(c_org, self.c_dim, 'CelebA', self.selected_attrs)
        c_rafd_list = self.create_labels(c_org, self.c2_dim, 'RaFD')
        zero_celeba = torch.zeros(x_fixed.size(0), self.c_dim).to(self.device)           # Zero vector for CelebA.
        zero_rafd = torch.zeros(x_fixed.size(0), self.c2_dim).to(self.device)             # Zero vector for RaFD.
        mask_celeba = self.label2onehot(torch.zeros(x_fixed.size(0)), 2).to(self.device)  # Mask vector: [1, 0].
        mask_rafd = self.label2onehot(torch.ones(x_fixed.size(0)), 2).to(self.device)     # Mask vector: [0, 1].

        # Learning rate cache for decaying.
        g_lr = self.g_lr
        d_lr = self.d_lr

        # Start training from scratch or resume training.
        start_iters = 0
        if self.resume_iters:
            start_iters = self.resume_iters
            self.restore_model(self.resume_iters)

        # Start training.
        print('Start training...')
        start_time = time.time()
        for i in range(start_iters, self.num_iters):
            for dataset in ['CelebA', 'RaFD']:

                # =================================================================================== #
                #                             1. Preprocess input data                                #
                # =================================================================================== #
                
                # Fetch real images and labels.
                data_iter = celeba_iter if dataset == 'CelebA' else rafd_iter
                
                try:
                    x_real, label_org = next(data_iter)
                except:
                    if dataset == 'CelebA':
                        celeba_iter = iter(self.celeba_loader)
                        x_real, label_org = next(celeba_iter)
                    elif dataset == 'RaFD':
                        rafd_iter = iter(self.rafd_loader)
                        x_real, label_org = next(rafd_iter)

                # Generate target domain labels randomly.
                rand_idx = torch.randperm(label_org.size(0))
                label_trg = label_org[rand_idx]

                if dataset == 'CelebA':
                    c_org = label_org.clone()
                    c_trg = label_trg.clone()
                    zero = torch.zeros(x_real.size(0), self.c2_dim)
                    mask = self.label2onehot(torch.zeros(x_real.size(0)), 2)
                    c_org = torch.cat([c_org, zero, mask], dim=1)
                    c_trg = torch.cat([c_trg, zero, mask], dim=1)
                elif dataset == 'RaFD':
                    c_org = self.label2onehot(label_org, self.c2_dim)
                    c_trg = self.label2onehot(label_trg, self.c2_dim)
                    zero = torch.zeros(x_real.size(0), self.c_dim)
                    mask = self.label2onehot(torch.ones(x_real.size(0)), 2)
                    c_org = torch.cat([zero, c_org, mask], dim=1)
                    c_trg = torch.cat([zero, c_trg, mask], dim=1)

                x_real = x_real.to(self.device)             # Input images.
                c_org = c_org.to(self.device)               # Original domain labels.
                c_trg = c_trg.to(self.device)               # Target domain labels.
                label_org = label_org.to(self.device)       # Labels for computing classification loss.
                label_trg = label_trg.to(self.device)       # Labels for computing classification loss.

                # =================================================================================== #
                #                             2. Train the discriminator                              #
                # =================================================================================== #

                # Compute loss with real images.
                out_src, out_cls = self.D(x_real)
                out_cls = out_cls[:, :self.c_dim] if dataset == 'CelebA' else out_cls[:, self.c_dim:]
                d_loss_real = - torch.mean(out_src)
                d_loss_cls = self.classification_loss(out_cls, label_org, dataset)

                # Compute loss with fake images.
                x_fake = self.G(x_real, c_trg)
                out_src, _ = self.D(x_fake.detach())
                d_loss_fake = torch.mean(out_src)

                # Compute loss for gradient penalty.
                alpha = torch.rand(x_real.size(0), 1, 1, 1).to(self.device)
                x_hat = (alpha * x_real.data + (1 - alpha) * x_fake.data).requires_grad_(True)
                out_src, _ = self.D(x_hat)
                d_loss_gp = self.gradient_penalty(out_src, x_hat)

                # Backward and optimize.
                d_loss = d_loss_real + d_loss_fake + self.lambda_cls * d_loss_cls + self.lambda_gp * d_loss_gp
                self.reset_grad()
                d_loss.backward()
                self.d_optimizer.step()

                # Logging.
                loss = {}
                loss['D/loss_real'] = d_loss_real.item()
                loss['D/loss_fake'] = d_loss_fake.item()
                loss['D/loss_cls'] = d_loss_cls.item()
                loss['D/loss_gp'] = d_loss_gp.item()
            
                # =================================================================================== #
                #                               3. Train the generator                                #
                # =================================================================================== #

                if (i+1) % self.n_critic == 0:
                    # Original-to-target domain.
                    x_fake = self.G(x_real, c_trg)
                    out_src, out_cls = self.D(x_fake)
                    out_cls = out_cls[:, :self.c_dim] if dataset == 'CelebA' else out_cls[:, self.c_dim:]
                    g_loss_fake = - torch.mean(out_src)
                    g_loss_cls = self.classification_loss(out_cls, label_trg, dataset)

                    # Target-to-original domain.
                    x_reconst = self.G(x_fake, c_org)
                    g_loss_rec = torch.mean(torch.abs(x_real - x_reconst))

                    # Backward and optimize.
                    g_loss = g_loss_fake + self.lambda_rec * g_loss_rec + self.lambda_cls * g_loss_cls
                    self.reset_grad()
                    g_loss.backward()
                    self.g_optimizer.step()

                    # Logging.
                    loss['G/loss_fake'] = g_loss_fake.item()
                    loss['G/loss_rec'] = g_loss_rec.item()
                    loss['G/loss_cls'] = g_loss_cls.item()

                # =================================================================================== #
                #                                 4. Miscellaneous                                    #
                # =================================================================================== #

                # Print out training info.
                if (i+1) % self.log_step == 0:
                    et = time.time() - start_time
                    self.log_training_info(et, loss, i)

            # Translate fixed images for debugging.
            if (i+1) % self.sample_step == 0:
                self.translate_samples_multi(i, x_fixed, c_celeba_list, c_rafd_list,
                                             zero_rafd, zero_celeba, mask_celeba, mask_rafd)

            # Save model checkpoints.
            if (i+1) % self.model_save_step == 0 or (i+1) == self.num_iters:
                self.save_checkpoints(i)

            # Decay learning rates.
            if (i+1) % self.lr_update_step == 0 and (i+1) > (self.num_iters - self.num_iters_decay):
                g_lr, d_lr = self.decay_learning_rates(g_lr, d_lr)

    def test(self):
        """Translate images using StarGAN trained on a single dataset."""
        # Load the trained generator.
        self.restore_model(self.test_iters)
        
        # Set data loader.
        if self.dataset == 'CelebA':
            data_loader = self.celeba_loader
        elif self.dataset == 'RaFD':
            data_loader = self.rafd_loader
        
        with torch.no_grad():
            for i, (x_real, c_org) in enumerate(data_loader):

                # Prepare input images and target domain labels.
                x_real = x_real.to(self.device)
                c_trg_list = self.create_labels(c_org, self.c_dim, self.dataset, self.selected_attrs)

                # Translate images.
                x_fake_list = [x_real]
                for c_trg in c_trg_list:
                    x_fake_list.append(self.G(x_real, c_trg))

                # Save the translated images.
                x_concat = torch.cat(x_fake_list, dim=3)
                result_path = os.path.join(self.result_dir, '{}-images.jpg'.format(i+1))
                save_image(self.denorm(x_concat.data.cpu()), result_path, nrow=1, padding=0)
                print('Saved real and fake images into {}...'.format(result_path))

    def test_multi(self):
        """Translate images using StarGAN trained on multiple datasets."""
        # Load the trained generator.
        self.restore_model(self.test_iters)
        
        with torch.no_grad():
            for i, (x_real, c_org) in enumerate(self.celeba_loader):

                # Prepare input images and target domain labels.
                x_real = x_real.to(self.device)
                c_celeba_list = self.create_labels(c_org, self.c_dim, 'CelebA', self.selected_attrs)
                c_rafd_list = self.create_labels(c_org, self.c2_dim, 'RaFD')
                zero_celeba = torch.zeros(x_real.size(0), self.c_dim).to(self.device)            # Zero vector for CelebA.
                zero_rafd = torch.zeros(x_real.size(0), self.c2_dim).to(self.device)             # Zero vector for RaFD.
                mask_celeba = self.label2onehot(torch.zeros(x_real.size(0)), 2).to(self.device)  # Mask vector: [1, 0].
                mask_rafd = self.label2onehot(torch.ones(x_real.size(0)), 2).to(self.device)     # Mask vector: [0, 1].

                # Translate images.
                x_fake_list = [x_real]
                for c_celeba in c_celeba_list:
                    c_trg = torch.cat([c_celeba, zero_rafd, mask_celeba], dim=1)
                    x_fake_list.append(self.G(x_real, c_trg))
                for c_rafd in c_rafd_list:
                    c_trg = torch.cat([zero_celeba, c_rafd, mask_rafd], dim=1)
                    x_fake_list.append(self.G(x_real, c_trg))

                # Save the translated images.
                x_concat = torch.cat(x_fake_list, dim=3)
                result_path = os.path.join(self.result_dir, '{}-images.jpg'.format(i+1))
                save_image(self.denorm(x_concat.data.cpu()), result_path, nrow=1, padding=0)
                print('Saved real and fake images into {}...'.format(result_path))