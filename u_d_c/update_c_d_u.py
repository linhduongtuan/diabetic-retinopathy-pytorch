import torch
from torch import nn
from torch.autograd import grad
from torch.optim import lr_scheduler

from u_d_c.base import base
from utils.tv_loss import TVLoss


class update_c_d_u(base):
    def __init__(self, args):
        base.__init__(self, args)
        self.alpha = args.alpha
        self.sigma = args.sigma
        self.lmbda = args.lmbda
        self.gamma = args.gamma
        self.theta = args.theta
        self.pretrained_steps = args.pretrained_steps
        self.cross_entropy = nn.CrossEntropyLoss().cuda()
        self.l1_criterion = nn.L1Loss(reduce=False).cuda()
        self.tv_loss_criterion = TVLoss().cuda()


    def train(self, epoch):
        for idx, data in enumerate(self.dataloader, 1):
            step = (epoch - 1) * (len(self.dataloader.dataset) // self.batch_size) + idx
            lesion_data, lesion_labels, _, lesion_gradient, real_data, normal_labels, _, normal_gradient = data
            if self.use_gpu:
                lesion_data, lesion_labels, normal_gradient = lesion_data.cuda(), lesion_labels.cuda(), normal_gradient.unsqueeze(
                    1).cuda()
                real_data, normal_labels, lesion_gradient = real_data.cuda(), normal_labels.cuda(), lesion_gradient.unsqueeze(
                    1).cuda()
            # update u & c
            self.u_optimizer.zero_grad()
            self.c_optimizer.zero_grad()
            inputs, labels, gradients = self.shuffle(lesion_data, real_data, lesion_labels, normal_labels,
                                                     lesion_gradient, normal_gradient)
            code = self.auto_encoder(inputs)
            c_loss = self.cross_entropy(self.classifier(code - inputs), labels)
            u_loss = (gradients * self.l1_criterion(code, inputs)).mean()

            u_c_loss = self.lmbda * u_loss + self.sigma * c_loss
            u_c_loss.backward()
            self.u_optimizer.step()
            self.c_optimizer.step()

            # training network: update d
            self.d_optimizer.zero_grad()
            fake_data = self.auto_encoder(lesion_data)
            real_dis_output = self.d(real_data)
            fake_dis_output = self.d(fake_data.detach())

            theta = torch.rand((real_data.size(0), 1, 1, 1))
            if self.use_gpu:
                theta = theta.cuda()
            x_hat = theta * real_data.data + (1 - theta) * fake_data.data
            x_hat.requires_grad = True
            pred_hat = self.d(x_hat)
            if self.use_gpu:
                gradients = grad(outputs=pred_hat, inputs=x_hat, grad_outputs=torch.ones(pred_hat.size()).cuda(),
                                 create_graph=True, retain_graph=True, only_inputs=True)[0]
            else:
                gradients = grad(outputs=pred_hat, inputs=x_hat, grad_outputs=torch.ones(pred_hat.size()),
                                 create_graph=True, retain_graph=True, only_inputs=True)[0]
            gradient_penalty = self.eta * ((gradients.view(gradients.size()[0], -1).norm(2, 1) - 1) ** 2).mean()

            d_real_loss = -torch.mean(real_dis_output)
            d_fake_loss = torch.mean(fake_dis_output)

            d_loss = d_real_loss + d_fake_loss + gradient_penalty
            d_loss.backward()
            self.d_optimizer.step()

            # update u
            if step > self.pretrained_steps:
                self.u_optimizer.zero_grad()
                dis_output = self.d(fake_data)
                d_loss_ = -torch.mean(dis_output)

                real_data_ = self.auto_encoder(real_data)
                normal_l1_loss = (normal_gradient * self.l1_criterion(real_data_, real_data)).mean()
                lesion_l1_loss = (lesion_gradient * self.l1_criterion(fake_data, lesion_data)).mean()
                # add total variable loss as a regularization term
                tv_loss = self.tv_loss_criterion((fake_data - lesion_data))
                u_loss_ = normal_l1_loss + lesion_l1_loss
                u_d_loss = self.alpha * d_loss_ + self.gamma * u_loss_ + self.theta * tv_loss
                u_d_loss.backward()

                self.u_optimizer.step()

                w_distance = d_real_loss.item() + d_fake_loss.item()
                info = {
                    'classifier_loss': self.sigma * c_loss.item(),
                    'unet_loss': self.gamma * u_loss_.item(),
                    'adversial_loss': self.alpha * d_loss_.item(),
                    'loss': u_loss.item(),
                    'w_distance': w_distance,
                    'lr': self.get_lr()
                }
                # for tag, value in info.items():
                #     self.logger.scalar_summary(tag, value, step)

                if idx % self.interval == 0:
                    log = '[%d/%d] %.3f=%.3f(u_loss)+%.3f(c_loss), %.3f=%.3f(d_real_loss)+%.3f(d_fake_loss)+%.3f(gradient_penalty), ' \
                          'w_distance: %.3f, %.3f(u_d_loss)=%.3f(d_loss_)+%.3f(normal_l1_loss)+%.3f(lesion_l1_loss)+%.3f(tv_loss)' % (
                              epoch, self.epochs, u_c_loss.item(), self.lmbda * u_loss.item(),
                              self.sigma * c_loss.item(),
                              d_loss.item(), d_real_loss.item(), d_fake_loss.item(), gradient_penalty.item(),
                              w_distance,
                              u_d_loss.item(), self.alpha * d_loss_.item(),
                              self.gamma * normal_l1_loss.item(), self.gamma * lesion_l1_loss.item(),
                              self.theta * tv_loss.item())
                    print(log)
                    self.log_lst.append(log)
