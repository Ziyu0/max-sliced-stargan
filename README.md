# Max-Sliced StarGAN
This repository contains Pytorch implementation for the _Max-Sliced StarGAN_ proposed in project [Multi-Domain Image-to-Image Translation using StarGAN with Max Sliced Wasserstein Distance](report/Multi_Domain_Image_to_Image_Translation_using_StarGAN_with_Max_Sliced_Wasserstein_Distance.pdf).

The Max-Sliced StarGAN combines [StarGAN](https://arxiv.org/abs/1711.09020) and [Max-Sliced Wasserstein distance](https://arxiv.org/abs/1904.05877) together to improve the training stability and reduce sample complexity of the orginal StarGAN.

Sample images generated by the Max-Sliced StarGAN are shown here.

<p align="center">
<img src=imgs/all_attr.png width=700>
</p>

## Dependencies
* [Python 3.5+](https://www.continuum.io/downloads)
* [PyTorch 0.4.0+](http://pytorch.org/)
* [TensorFlow 1.3+](https://www.tensorflow.org/) (optional for tensorboard)

## Usage

> Note: the current version only supports training on the CelebA dataset.

### 1. Clone the repository
```
git clone https://github.com/Ziyu0/max-sliced-stargan.git
cd max-sliced-stargan
```

### 2. Download the CelebA dataset
```
bash download.sh celeba
```

### 3. Training

Run 
```
python main.py --help
```
to see all the configurable hyper-parameters.

#### Training the original StarGAN
```
cd scripts
bash train_celeba_original.sh
```

#### Training the Max-Sliced StarGAN
```
cd scripts
bash train_celeba_max_sliced.sh 
```
In script `train_celeba_max_sliced.sh`, `--use_max_sw_loss` is set to `True` to enable the max-sliced Wasserstein distance.

#### Training the other baseline models

> Please refer to the [report](report/Multi_Domain_Image_to_Image_Translation_using_StarGAN_with_Max_Sliced_Wasserstein_Distance.pdf) for the introduction to the baseline models

* Training the Sliced StarGAN
    ```
    cd scripts
    bash train_celeba_sliced.sh
    ```
    In script `train_celeba_sliced.sh`, `--use_sw_loss` is set to `True` to enable the sliced Wasserstein distance.
* Training the Sliced StarGAN with feature transformation
    ```
    cd scripts
    bash train_celeba_sliced_feat_trans.sh
    ```
    In the script `train_celeba_sliced_feat_trans.sh`, both `--use_sw_loss` and `--use_d_feature` are set to `True` so that we can compute the sliced Wasserstein distance based on the feature transformation.

### 4. Testing
#### Testing on all images from the test dataset
```
cd scripts
bash test_celeba_general.sh 
```

#### Testing on on a small subset of the images from the test dataset
```
cd scripts
bash test_celeba_small.sh
```

### 5. Plot
To generate loss plots for multiple training processes, run
```
cd scripts
bash create_plots.sh
```

Here is a sample plot:

<p align="center">
<img src=imgs/G_loss_rec.png height=450>
</p>

## Results
The following figure is the facial attribute transfer results for the original StarGAN and the Max-Sliced StarGAN. Four sets of generated images are shown from the top left to the bottom right sections. For each section, the first column shows the input image, and the next three columns show the single attribute transfer results.

<p align="center">
<img src=imgs/origin_and_max.png width=800>
</p>