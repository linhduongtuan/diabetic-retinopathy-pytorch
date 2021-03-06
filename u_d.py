"""
u+d architecture: pre-trained unet + wgan-gp(lambda=10.0 and slope of leaky_relu is 0.2 in default).
usage:

python u_d.py -b=90 -e=250 -i=12 -p=gan49 -l=4.9 -a=0.1 -n=2 -k=2 --step_size=200 --d_depth=6 --dowmsampling=3 --u_depth=4
"""
import sys
import numpy as np
import argparse
import torch


sys.path.append('./')
from u_d import *

SEED = 100
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)
np.random.seed(SEED)

def parse_args():
    parser = argparse.ArgumentParser(description='Training Custom Defined Model')
    parser.add_argument('-ts', '--training_strategies', type=str, default='wgan-gp', choices=['wgan-gp'], help='training strategies')
    parser.add_argument('-b', '--batch_size', type=int, required=True, help='batch size')
    parser.add_argument('-e', '--epochs', type=int, default=350, help='training epochs')
    parser.add_argument('--lr', type=float, default=2e-4, help='learning rate')
    parser.add_argument('-i', '--interval', type=int, default=20, help='log print interval')
    parser.add_argument('-p', '--prefix', type=str, required=True, help='parent folder to save result')
    parser.add_argument('-a', '--alpha', type=float, default=1, help='weight of d in u & d')
    parser.add_argument('-l', '--lmbda', type=float, default=0.2, help='weight of u in u & d')
    parser.add_argument('--gamma', type=float, default=10.0, help='gradient penalty')
    parser.add_argument('--beta1', type=float, default=0.0, help='beta1 in Adam')
    parser.add_argument('-n', '--n_update_gan', type=int, default=1, help='update gan(unet) frequence')
    parser.add_argument('-u', '--is_pretrained_unet', action='store_true', help='pretrained unet or not')
    parser.add_argument('--pretrain_unet_path', type=str, default='./identical_mapping45/identical_mapping.pkl', help='pretrained unet')
    parser.add_argument('--pretrained_epochs', type=int, default=0, help='pretrained epochs for d')
    parser.add_argument('-d', '--data', type=str, default='./data/gan', choices=['./data/gan'], help='dataset dir')
    parser.add_argument('-k', '--power', type=int, default=2, help='power of gradient weight matrix')
    parser.add_argument('--gan_type', type=str, default='multi_scale',
                        choices=['conv_bn_leaky_relu', 'multi_scale'],
                        help='discriminator type')
    parser.add_argument('--d_depth', type=int, default=7, help='discriminator depth')
    parser.add_argument('--u_depth', type=int, default=5, help='unet dpeth')
    parser.add_argument('--dowmsampling', type=int ,default=4, help='dowmsampling times in discriminator')
    parser.add_argument('--debug', action='store_true', default=False, help='in debug or not(default: false)')
    parser.add_argument('--gpu_counts', default=torch.cuda.device_count(), type=int, help='gpu nums')

    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    if args.training_strategies == 'wgan-gp':
        trainer = gan(args)
        script_path = './u_d/gan.py'
        print('update u & d')
    else:
        raise ValueError('')
    trainer.save_running_script(script_path)
    trainer.main()
    trainer.save_log()


if __name__ == '__main__':
    main()
