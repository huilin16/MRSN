# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import os

import paddle

from paddleseg.cvlibs import manager, Config
from paddleseg.utils import get_sys_env, logger, config_check
from paddleseg.core import predict


def parse_args():
    parser = argparse.ArgumentParser(description='Model prediction')

    # params of prediction
    parser.add_argument(
        "--config", dest="cfg", help="The config file.", default=None, type=str)
    parser.add_argument(
        '--model_path',
        dest='model_path',
        help='The path of model for prediction',
        type=str,
        default=None)
    parser.add_argument(
        '--image_path',
        dest='image_path',
        help=
        'The path of image, it can be a file or a directory including images',
        type=str,
        default=None)
    parser.add_argument(
        '--image_path2',
        dest='image_path2',
        help=
        'The path of image, it can be a file or a directory including images',
        type=str,
        default=None)
    parser.add_argument(
        '--save_dir',
        dest='save_dir',
        help='The directory for saving the predicted results',
        type=str,
        default='./output/result')

    # augment for prediction
    parser.add_argument(
        '--save_logit',
        dest='save_logit',
        help='Whether to use mulit-scales and flip augment for prediction',
        action='store_true')
    parser.add_argument(
        '--aug_pred',
        dest='aug_pred',
        help='Whether to use mulit-scales and flip augment for prediction',
        action='store_true')
    parser.add_argument(
        '--swap',
        dest='swap',
        help='Whether to swap images for evaluation',
        type=int,
        default=0)
    parser.add_argument(
        '--scales',
        dest='scales',
        nargs='+',
        help='Scales for augment',
        type=float,
        default=1.0)
    parser.add_argument(
        '--flip_horizontal',
        dest='flip_horizontal',
        help='Whether to use flip horizontally augment',
        action='store_true')
    parser.add_argument(
        '--flip_vertical',
        dest='flip_vertical',
        help='Whether to use flip vertically augment',
        action='store_true')

    # sliding window prediction
    parser.add_argument(
        '--is_slide',
        dest='is_slide',
        help='Whether to prediction by sliding window',
        action='store_true')
    parser.add_argument(
        '--crop_size',
        dest='crop_size',
        nargs=2,
        help=
        'The crop size of sliding window, the first is width and the second is height.',
        type=int,
        default=None)
    parser.add_argument(
        '--stride',
        dest='stride',
        nargs=2,
        help=
        'The stride of sliding window, the first is width and the second is height.',
        type=int,
        default=None)
    parser.add_argument(
        '--batch_size',
        dest='batch_size',
        help='Mini batch size of one gpu or cpu',
        type=int,
        default=1)
    parser.add_argument(
        '--patch_size',
        dest='patch_size',
        help='Mini batch size of one gpu or cpu, work when silde_infer',
        type=int,
        default=1)

    return parser.parse_args()


def get_image_list(image_path):
    """Get image list"""
    valid_suffix = [
        '.JPEG', '.jpeg', '.JPG', '.jpg', '.BMP', '.bmp', '.PNG', '.png', '.tif', '.tiff'
    ]
    image_list = []
    image_dir = None
    if os.path.isfile(image_path):
        if os.path.splitext(image_path)[-1] in valid_suffix:
            image_list.append(image_path)
        else:
            image_dir = os.path.dirname(image_path)
            with open(image_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if len(line.split()) > 1:
                        line = line.split()[0]
                    image_list.append(os.path.join(image_dir, line))
    elif os.path.isdir(image_path):
        image_dir = image_path
        for root, dirs, files in os.walk(image_path):
            for f in files:
                if '.ipynb_checkpoints' in root:
                    continue
                if os.path.splitext(f)[-1] in valid_suffix:
                    image_list.append(os.path.join(root, f))
    else:
        raise FileNotFoundError(
            '`--image_path` is not found. it should be an image file or a directory including images'
        )

    if len(image_list) == 0:
        raise RuntimeError('There are not image file in `--image_path`')

    return image_list, image_dir


def get_test_config(cfg, args):

    test_config = cfg.test_config
    if args.aug_pred:
        test_config['aug_pred'] = args.aug_pred
        test_config['scales'] = args.scales
        test_config['swap'] = args.swap
        test_config['save_logit'] = args.save_logit

    if args.flip_horizontal:
        test_config['flip_horizontal'] = args.flip_horizontal

    if args.flip_vertical:
        test_config['flip_vertical'] = args.flip_vertical

    if args.is_slide:
        test_config['is_slide'] = args.is_slide
        test_config['crop_size'] = args.crop_size
        test_config['stride'] = args.stride

    return test_config


def main(args):
    env_info = get_sys_env()
    place = 'gpu' if env_info['Paddle compiled with cuda'] and env_info[
        'GPUs used'] else 'cpu'

    paddle.set_device(place)
    if not args.cfg:
        raise RuntimeError('No configuration file specified.')

    cfg = Config(args.cfg)
    val_dataset = cfg.val_dataset
    if not val_dataset:
        raise RuntimeError(
            'The verification dataset is not specified in the configuration file.'
        )

    msg = '\n---------------Config Information---------------\n'
    msg += str(cfg)
    msg += '------------------------------------------------'
    logger.info(msg)

    model = cfg.model
    transforms = val_dataset.transforms
    image_list, image_dir = get_image_list(args.image_path)
    logger.info('Number of predict images = {}'.format(len(image_list)))

    test_config = get_test_config(cfg, args)
    config_check(cfg, val_dataset=val_dataset)

    predict(
        model,
        image_dir=image_dir,
        image_dir2 = args.image_path2,
        batch_size=args.batch_size,
        patch_size=args.patch_size,
        model_path=args.model_path,
        transforms=transforms,
        image_list=image_list,
        save_dir=args.save_dir,
        **test_config)


if __name__ == '__main__':
    args = parse_args()
    main(args)
