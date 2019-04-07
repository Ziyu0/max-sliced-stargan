import numpy as np
import torch
import torch.nn.functional as F


def sliced_wasserstein_distance(true_samples, fake_samples, num_projections):
    """Compute Sliced Wasserstein Distance between real samples and
    generated samples.

    TODO: before passing into this funciton, flattern 
        feature_size = width * height * 3
        or change dimension inside of this function
        => Need to check the dimension of images provided by data loader

    Args:
        true_samples: Samples from the real dataset, shape
            (N, num_features), where N = num of samples or batch size
        fake_samples: Samples from the generator, shape
            (N, num_features), where N = num of samples or batch size
    Returns:
        Sliced Wasserstein Distance, a scalar
    """
    num_features = true_samples.shape[1]

    # Random projection directions, shape (num_features, num_projections)
    projections = np.random.normal(size=(num_features, num_projections))
    projections = F.normalize(torch.from_numpy(projections), p=2, dim=0)

    # Project the samples along the directions, get shape (N, num_projections)
    # Then transpose to (num_projections, N), format [projected_image1, projected_image2, ...]
    projected_true = torch.matmul(true_samples, projections).transpose(0, 1)
    projected_fake = torch.matmul(fake_samples, projections).transpose(0, 1)

    # For each projection direction (row), sort the images
    sorted_true = torch.sort(projected_true, dim=1)[0]
    sorted_fake = torch.sort(projected_fake, dim=1)[0]

    # Get Wasserstein-2 distance averaged over samples and directions
    return torch.pow(sorted_true - sorted_fake, 2).mean()


