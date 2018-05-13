
from __future__ import print_function

import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import random, sys, os, json

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable

from models import DecodingNet
from torchvision import models
from utils import *

from skimage import filters
from skimage.morphology import binary_dilation
import IPython

import transforms
#from transforms import rotate, scale, flip, resize, gauss, noise, resize_rect, translate

EPSILON = 3e-2
MIN_LOSS = 7e-2
BATCH_SIZE = 12


def encode_binary(image, model, target, max_iter=2000, verbose=False):

    image = im.torch(image)
    perturbation_old = None
    
    if USE_CUDA: perturbation = nn.Parameter(torch.randn(image.size()).cuda()+0.0)
    else: perturbation = nn.Parameter(torch.randn(image.size())+0.0)

    # returns an image after a series of transformations
    def distribution(x):
        x = transforms.resize_rect(x)
        x = transforms.rotate(transforms.scale(x), max_angle=90)
        x = transforms.resize(x, rand_val=False, resize_val=224)
        x = transforms.translate(x)
        x = transforms.gauss(x, min_sigma=0.8, max_sigma=1.2)
        return x

    # returns the loss for the image
    def loss_func(model, x):
        predictions = model.forward(x, distribution=distribution, n=BATCH_SIZE)
        return F.mse_loss(predictions, binary.target(target)), predictions.cpu().data.numpy().round(2)


    opt = torch.optim.Adam([perturbation], lr=0.1)

    losses = []
    preds = []
    for i in range(0, max_iter):

        def closure():
            opt.zero_grad()

            # perform projected gradient descent by norm bounding the perturbation
            perturbation_zc = (perturbation - perturbation.mean())/(perturbation.std()) * EPSILON
            changed_image = (image + perturbation_zc).clamp(min=0.1, max=0.99)
            
            loss, predictions = loss_func(model, changed_image)
            loss.backward()

            preds.append(predictions)
            losses.append(loss.cpu().data.numpy())

            return loss

        opt.step(closure)

        if i % 20 == 0:
            
            perturbation_zc = (perturbation - perturbation.mean())/(perturbation.std()) * EPSILON
            if (perturbation_old is None): perturbation_old = perturbation_zc

            changed_image = (image + perturbation_zc).clamp(min=0.1, max=0.99)

            if verbose:
                print ("Loss: ", np.mean(losses[-20:]))
                #print ("Predictions: ", np.round(np.mean(preds[-20:], axis=0), 2))
                #print ("Modified prediction: ", binary.str(binary.get(model(changed_image))))
                
                #save(image, file="images/image.jpg")
                im.save(im.numpy(perturbation), file="/output/perturbation.jpg")
                im.save(im.numpy(changed_image), file="/output/changed_image.jpg")

        smooth_loss = np.mean(losses[-20:])
        if smooth_loss <= MIN_LOSS:
            break

    perturbation_zc = (perturbation - perturbation.mean())/(perturbation.std()) * EPSILON
    changed_image = (image + perturbation_zc).clamp(min=0.1, max=0.99)

    im.save(im.numpy(perturbation), file="/output/perturbation.jpg")
    im.save(im.numpy(changed_image), file="/output/changed_image.jpg")
    
    # if verbose:
    #     #print("pert max : ", perturbation_zc.data.cpu().numpy().max(), "\tmin: ", perturbation_zc.data.cpu().numpy().min())
    #     plt.plot(np.array(preds)); plt.savefig("/output/preds.jpg"); plt.cla()
    #     plt.plot(losses); plt.savefig("/output/loss.jpg"); plt.cla()
    #     #print ("Original predictions: ", binary.get(model(image)))
    #     #print ("Perturbation: ", binary.get(model(perturbation_zc)))
    #     print ("Modified prediction: ", binary.get(model(changed_image)))
    #     #print ("Final predictions: ", preds[-1])

    return im.numpy(changed_image)

if __name__ == "__main__":
    target = binary.random(n=TARGET_SIZE)
    model = DecodingNet()
    print("Target: ", binary.str(target))
    encode_binary(im.load("images/cat.jpg"), model, target=target, verbose=True)
