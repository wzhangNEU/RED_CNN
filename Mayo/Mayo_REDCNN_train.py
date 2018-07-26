
import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from Mayo_REDCNN_dataloader import DCMsDataset
from Mayo_REDCNN_model import RED_CNN

def update_lr(optimizer, lr):
    for param_group in optimizer.param_groups:
        param_group["lr"] = lr


### full CT img training
full_data_path = '/data1/Mayo-CT-full/'
full_data_dir = os.listdir(full_data_path)

input_img_dir = full_data_path + full_data_dir[0]
target_img_dir = full_data_path + full_data_dir[1]

LEARNING_RATE = 1e-4
NUM_EPOCHS = 1000
BATCH_SIZE = 4
OUT_CHANNELS = 96

dcm = DCMsDataset(input_img_dir, target_img_dir)
dcm_loader = DataLoader(dcm, batch_size=BATCH_SIZE, shuffle=True, num_workers=8)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

red_cnn = RED_CNN(OUT_CHANNELS)

if torch.cuda.device_count() > 1:
    print("Use {} GPUs".format(torch.cuda.device_count()), "="*10)
    red_cnn = nn.DataParallel(red_cnn)
red_cnn.to(device)

criterion = nn.MSELoss()
optimizer = torch.optim.Adam(red_cnn.parameters(), lr=LEARNING_RATE)

total_step = len(dcm_loader)
current_lr = LEARNING_RATE

loss_lst = []
for epoch in range(NUM_EPOCHS):
    for i, (inputs, targets) in enumerate(dcm_loader):
        input_img = torch.tensor(inputs, requires_grad=True, dtype=torch.float32).unsqueeze(1).to(device)
        target_img = torch.tensor(targets, dtype=torch.float32).unsqueeze(1).to(device)

        outputs = red_cnn(input_img)
        loss = criterion(outputs, target_img)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if (i+1) % 10 == 0:
            print('EPOCH [{}/{}], STEP [{}/{}], LOSS {:.4f}'.format(epoch+1, NUM_EPOCHS, i+1, total_step, loss.item()))

        if (epoch+1) % 100 == 0:
            current_lr /= 1.1
            update_lr(optimizer, current_lr)

        if (epoch+1) % 100 == 0:
            torch.save(red_cnn.state_dict(), 'red_cnn_mayo_{}ep.ckpt'.format(epoch+1))

        loss_lst.append(loss.item())
