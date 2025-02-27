import torch
import numpy as np
import sys
import getopt
import os
import shutil
import matplotlib.pyplot as plt
import datetime
from Network import TOFlow
import warnings
import pdb

warnings.filterwarnings("ignore", module="matplotlib.pyplot")
# ------------------------------
# I don't know whether you have a GPU.
plt.switch_backend('agg')
# Static
task = ''
dataset_dir = ''
pathlistfile = ''
model_path = ''
gpuID = None

if sys.argv[1] in ['-h', '--help']:
    print("""pytoflow version 1.0
usage: python3 train.py [[option] [value]]...
options:
--task         training task, like slow, clean, zoom
               valid values:[slow, denoise, clean, sr, zoom]
--dataDir      the directory of the input image dataset(Vimeo-90K, Vimeo-90K with noise, blurred Vimeo-90K)
--pathlist     the text file records which are the images for train.
--model        the path of the model used.
--gpuID        the No. of the GPU you want to use.
--help         get help.""")
    exit(0)

for strOption, strArgument in getopt.getopt(sys.argv[1:], '', [strParameter[2:] + '=' for strParameter in sys.argv[1::2]])[0]:
    if strOption == '--task':           # task
        task = strArgument
    elif strOption == '--dataDir':      # dataset_dir
        dataset_dir = strArgument
    elif strOption == '--pathlist':     # pathlist file
        pathlistfile = strArgument
    elif strOption == '--model':        # model path
        model_path = strArgument
    elif strOption == '--gpuID':        # gpu id
        gpuID = int(strArgument)

if task == '':
    raise ValueError('Missing [--task].\nPlease enter the training task.')
elif task not in ['slow', 'denoise', 'clean', 'sr', 'zoom']:
    raise ValueError('Invalid [--task].\nOnly support: [slow, denoise/clean, sr/zoom]')

if dataset_dir == '':
    raise ValueError('Missing [--dataDir].\nPlease provide the directory of the dataset. (Vimeo-90K)')

if pathlistfile == '':
    raise ValueError('Missing [--pathlist].\nPlease provide the pathlist index file for test.')

if model_path == '':
    raise ValueError('Missing [--model model_path].\nPlease provide the path of the toflow model.')

if gpuID == None:
    cuda_flag = False
else:
    cuda_flag = True
    torch.cuda.set_device(gpuID)
# --------------------------------------------------------------

def mkdir_if_not_exist(path):
    if not os.path.exists(path):
        os.mkdir(path)

def vimeo_evaluate(input_dir, out_img_dir, test_codelistfile, task='', cuda_flag=True):
    mkdir_if_not_exist(out_img_dir)

    net = TOFlow(task=task)
    net.load_state_dict(torch.load(model_path, map_location='cpu'))
    # pdb.set_trace()
    # model_path -- 'toflow_models/sr.pkl'

    if cuda_flag:
        net.cuda().eval()
    else:
        net.eval()

    fp = open(test_codelistfile)
    test_img_list = fp.read().splitlines()
    fp.close()

    if task == 'slow':
        process_index = [1, 3]
        str_format = 'im%d.png'
    elif task in ['slow', 'clean', 'zoom']:
        process_index = [1, 2, 3, 4, 5, 6, 7]
        str_format = 'im%04d.png'
    else:
        raise ValueError('Invalid [--task].\nOnly support: [slow, denoise/clean, sr/zoom]')
    total_count = len(test_img_list)
    count = 0
    # pdb.set_trace()
    # test_img_list -- ['00035/0737', '00053/0807', '00052/0159', '00034/0948', '00053/0337', '00071/0347', '00091/0333', '00067/0741']

    pre = datetime.datetime.now()
    for code in test_img_list:
        # print('Processing %s...' % code)
        count += 1
        video = code.split('/')[0]
        sep = code.split('/')[1]
        mkdir_if_not_exist(os.path.join(out_img_dir, video))
        mkdir_if_not_exist(os.path.join(out_img_dir, video, sep))
        input_frames = []
        for i in process_index:
            image = plt.imread(os.path.join(input_dir, code, str_format % i))
            output_filename = os.path.join(out_img_dir, video, sep, task + "_" + str_format % i)
            plt.imsave(output_filename, image)

            input_frames.append(plt.imread(os.path.join(input_dir, code, str_format % i)))
        # (Pdb) len(input_frames), input_frames[0].shape
        # (7, (256, 448, 3))

        input_frames = np.transpose(np.array(input_frames), (0, 3, 1, 2))

        if cuda_flag:
            input_frames = torch.from_numpy(input_frames).cuda()
        else:
            input_frames = torch.from_numpy(input_frames)
        input_frames = input_frames.view(1, input_frames.size(0), input_frames.size(1), input_frames.size(2), input_frames.size(3))

        predicted_img = net(input_frames)[0, :, :, :]
        # input_frames -- torch.Size([1, 7, 3, 256, 448])
        # predicted_img.size() -- torch.Size([3, 256, 448])


        predicted_img = predicted_img.clamp(0, 1.0)
        plt.imsave(os.path.join(out_img_dir, video, sep, task + '_out.png'),predicted_img.permute(1, 2, 0).cpu().detach().numpy())

        cur = datetime.datetime.now()
        processing_time = (cur - pre).seconds / count
        print('%.2fs per frame.\t%.2fs left.' % (processing_time, processing_time * (total_count - count)))

vimeo_evaluate(dataset_dir, './output', pathlistfile, task=task, cuda_flag=cuda_flag)