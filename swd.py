import numpy as np
import torch
import torch.nn.functional as F


def sliced_wasserstein_distance(true_samples, fake_samples, num_projections, device):
    """Compute Sliced Wasserstein Distance between real samples and
    generated samples.

    Args:
        true_samples(tensor): Samples from the real dataset, shape (N, num_features)
            Need to reshape images of (N, C, H, W) to (N, num_features) beforehand
        fake_samples(tensor): Samples from the generator, shape (N, num_features)
        num_projections(int)
        device(str): device used when training
    Returns:
        Sliced Wasserstein Distance, a scalar
    """

    # FIXME: loss is very close to 0 all the time -> vanishing gradient?

    num_features = true_samples.shape[1]

    # Random projection directions, shape (num_features, num_projections)
    projections = np.random.normal(size=(num_features, num_projections)).astype(np.float32)
    projections = F.normalize(torch.from_numpy(projections), p=2, dim=0)
    projections = torch.FloatTensor(projections).to(device)

    # Project the samples along the directions, get shape (N, num_projections)
    # Then transpose to (num_projections, N), format [projected_image1, projected_image2, ...]
    projected_true = torch.matmul(true_samples, projections).transpose(0, 1)
    projected_fake = torch.matmul(fake_samples, projections).transpose(0, 1)

    # For each projection direction (row), sort the images
    sorted_true = torch.sort(projected_true, dim=1)[0]
    sorted_fake = torch.sort(projected_fake, dim=1)[0]

    # Get Wasserstein-2 distance averaged over samples and directions
    return torch.pow(sorted_true - sorted_fake, 2).mean()


def max_sliced_wasserstein_distance(max_projected_true, max_projected_fake, device):
    """
    Before calling this func, pass true_samples and fake_samples to D and 
    return the outputs (max_projected_true, max_projected_fake) of D's last 
    FC layer. The D can now be written as [w^T h] (w - weights of a FC layer, 
    h - adversarially learnt feature space produced by D's penultimate layer).
    
    This is equivalent to projecting the samples onto the the max projection 
    direction that maximizes the projected Wasserstein distance in the 
    feature space.
    
    Args:
        max_projected_true(tensor)
        max_projected_fake(tensor)
        device(str)
    """

    # Sort the max projection. If it has more than 1 component, sort by row.
    # TODO: clarify the out_features of the FC layer
    sorted_true = torch.sort(max_projected_true, dim=1)[0]
    sorted_fake = torch.sort(max_projected_fake, dim=1)[0]    

    # Get Wasserstein-2 distance
    # TODO: not sure if we need to take the average
    return torch.pow(sorted_true - sorted_fake, 2)
