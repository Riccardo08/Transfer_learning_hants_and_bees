#TODO: TRANSFER LEARNING FOR COMPUTER VISION TUTORIAL (hants and bees)

from __future__ import print_function, division
import torch
import torch.nn as nn # All neural network models, nn.Linear, nn.Conv2d, BatchNorm, Loss functions
import torch.optim as optim # For all optimization algoritms, SGD, Adam, etc.
from torch.optim import lr_scheduler # To change (update) the learning rate.
import torch.nn.functional as F # All functions that don't have any parameters.
import numpy as np
import torchvision
from torchvision import datasets # Has standard datasets that we can import in a nice way.
from torchvision import models
from torchvision import transforms # Transormations we can perform on our datasets.
import matplotlib.pyplot as plt
import time
import os
import copy

plt.ion()   # interactive mode

#TODO: Load data

# Data augmentation and normalization for training
# Just normalization for validation
data_transforms = {
    'train': transforms.Compose([
        transforms.RandomResizedCrop(224),  # Crops the given image at the center; Crop a random portion of image and resize it to a given size.
                                            # If the image is torch Tensor, it is expected to have […, H, W] shape,
                                            # where … means an arbitrary number of leading dimensions. If image size is smaller
                                            # than output size along any edge, image is padded with 0 and then center cropped.
        transforms.RandomHorizontalFlip(),  # Horizontally flip the given image randomly with a given probability. If the image
                                            # is torch Tensor, it is expected to have […, H, W] shape, where … means an arbitrary number of leading dimensions
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]) # numbers writed on pytorch torchvision.transform library.
    ]),
    'val': transforms.Compose([
        transforms.Resize(256), # Resize the input image to the given size. If the image is torch Tensor, it is expected to have […, H, W] shape, where … means an arbitrary number of leading dimensions.
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
}

# data_dir = 'data/hymenoptera_data'
data_dir = "C:\\Users\\ricme\\Desktop\\Politecnico\\Tesi magistrale\\TL_coding\\hants_and_bees\\data\\hymenoptera_data"

image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x])
                  for x in ['train', 'val']}

dataloaders = {x: torch.utils.data.DataLoader(image_datasets[x], batch_size=4, shuffle=True, num_workers=4)
                for x in ['train', 'val']}

dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}

class_names = image_datasets['train'].classes

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

#TODO: Visualize a few images


# Get a batch of training data
inputs, classes = next(iter(dataloaders['train']))

# Make a grid from batch
out = torchvision.utils.make_grid(inputs)

imshow(out, title=[class_names[x] for x in classes])

#TODO: Training the model
def train_model(model, criterion, optimizer, scheduler, num_epochs=25):
    since = time.time()

    # deepcopy: constructs a new compound object and then, recursively, inserts copies into it of the objects found in the original.
    best_model_wts = copy.deepcopy(model.state_dict()) # 'state_dict' mappa ogni layer col suo tensore dei parametri
    best_acc = 0.0

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 20)

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()  # Set model to training mode
            else:
                model.eval()   # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # Iterate over data.
            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                # track history if only in train
                with torch.set_grad_enabled(phase == 'train'): #set_grad_enabled(True or False): Context-manager that sets gradient calculation to on or off
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    # Backward + optimize only if in training phase
                    if phase == 'train':
                        loss.backward() #loss.backward() computes dloss/dx for every parameter x which has requires_grad=True. These are accumulated into x.grad for every parameter x.
                        optimizer.step()

                # Statistics
                running_loss += loss.item() * inputs.size(0) #input.size(0) ??????????
                running_corrects += torch.sum(preds == labels.data)

            if phase == 'train':
                scheduler.step() # if we don’t call it, the learning rate won’t be changed and stays at the initial value.

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print('{} Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))

            # deep copy the model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())

        print()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))

    # load best model weights
    model.load_state_dict(best_model_wts)
    return model, best_acc

#TODO: Visualizing the model predictions (Generic function to display predictions for a few images)
def visualize_model(model, num_images=6):
    was_training = model.training
    model.eval()
    images_so_far = 0
    fig = plt.figure()

    with torch.no_grad():
        for i, (inputs, labels) in enumerate(dataloaders['val']):
            inputs = inputs.to(device)
            labels = labels.to(device)

            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)

            for j in range(inputs.size()[0]):
                images_so_far += 1
                ax = plt.subplot(num_images//2, 2, images_so_far)
                ax.axis('off')
                ax.set_title('predicted: {}'.format(class_names[preds[j]]))
                imshow(inputs.cpu().data[j])

                if images_so_far == num_images:
                    model.train(mode=was_training)
                    return
        model.train(mode=was_training)



#TODO: FINE-TUNING the convnet (Load a pretrained model and reset final fully connected layer)-------- parameters are all updated
print('FINE-TUNING')
model_ft = models.resnet18(pretrained=True) # optimize weights
print(model_ft)
num_ftrs = model_ft.fc.in_features # change the last fully connected layer
# Here the size of each output sample is set to 2.
# Alternatively, it can be generalized to nn.Linear(num_ftrs, len(class_names)).
model_ft.fc = nn.Linear(num_ftrs, 2)

model_ft = model_ft.to(device)

criterion = nn.CrossEntropyLoss()

# Observe that all parameters are being optimized
optimizer_ft = optim.SGD(model_ft.parameters(), lr=0.001, momentum=0.9)

# Decay LR (learning rate) by a factor of 0.1 every 7 epochs
exp_lr_scheduler = lr_scheduler.StepLR(optimizer_ft, step_size=7, gamma=0.1)


#TODO:Train and evaluate
model_ft, fine_tuning_acc = train_model(model_ft, criterion, optimizer_ft, exp_lr_scheduler, num_epochs=25)

visualize_model(model_ft)



#TODO: ConvNet as FIXED FEATURE EXTRACTOR (Here, we need to freeze all the network except the final layer. We need to
# set requires_grad == False to freeze the parameters so that the gradients are not computed in backward() ) -------- only parameters of the last layera are updated
print('FIXED FEATURES EXTRACTOR')
model_conv = torchvision.models.resnet18(pretrained=True)
print(model_conv)
for param in model_conv.parameters():
    param.requires_grad = False #freeze all the layers in the beginning and then we set a new last fully connected layer

# Parameters of newly constructed modules have requires_grad=True by default
num_ftrs = model_conv.fc.in_features
model_conv.fc = nn.Linear(num_ftrs, 2) #set the inlet features of the fc layer; the outputs are 2 (2 classes)

model_conv = model_conv.to(device)

criterion = nn.CrossEntropyLoss()

# Observe that only parameters of final layer are being optimized as opposed to before.
optimizer_conv = optim.SGD(model_conv.fc.parameters(), lr=0.001, momentum=0.9)

# Decay LR by a factor of 0.1 every 7 epochs
exp_lr_scheduler = lr_scheduler.StepLR(optimizer_conv, step_size=7, gamma=0.1)

#TODO: Train and evaluate
model_conv, feature_extractor_acc = train_model(model_conv, criterion, optimizer_conv, exp_lr_scheduler, num_epochs=25)

visualize_model(model_conv)

plt.ioff()
plt.show()

