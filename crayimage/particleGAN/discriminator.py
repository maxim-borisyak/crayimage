from ..nn import Expression
from ..nn.layers import conv_companion, make_cnn

import theano.tensor as T

from lasagne import *

__all__ = [
  'SimpleDiscriminator',
  'DeeplySupervisedDiscriminator',
  'StairsDiscriminator'
]

class SimpleDiscriminator(Expression):
  def __init__(self, img_shape=(1, 128, 128), noise_sigma=1.0 / (2 ** 11)):
    self.input_layer = layers.InputLayer(
      shape=(None,) + img_shape,
      name='input'
    )

    noise = layers.GaussianNoiseLayer(self.input_layer, sigma=noise_sigma, name='noise')

    conv1 = layers.Conv2DLayer(
      noise,
      num_filters=8, filter_size=(3, 3),
      pad='valid',
      nonlinearity=nonlinearities.softplus,
      name='conv1'
    )

    pool1 = layers.MaxPool2DLayer(
      conv1, pool_size=(2, 2),
      name='pool1'
    )

    conv2 = layers.Conv2DLayer(
      pool1,
      num_filters=16, filter_size=(3, 3),
      pad='valid',
      nonlinearity=nonlinearities.softplus,
      name='conv2'
    )

    pool2 = layers.MaxPool2DLayer(
      conv2, pool_size=(2, 2),
      name='pool2'
    )

    conv3 = layers.Conv2DLayer(
      pool2,
      num_filters=32, filter_size=(3, 3),
      pad='valid',
      nonlinearity=nonlinearities.softplus,
      name='conv3'
    )

    pool3 = layers.MaxPool2DLayer(
      conv3, pool_size=(2, 2),
      name='pool3'
    )

    conv4 = layers.Conv2DLayer(
      pool3,
      num_filters=64, filter_size=(3, 3),
      pad='valid',
      nonlinearity=nonlinearities.softplus,
      name='conv4'
    )

    pool4 = layers.MaxPool2DLayer(
      conv4, pool_size=(2, 2),
      name='pool3'
    )

    conv5 = layers.Conv2DLayer(
      pool4,
      num_filters=128, filter_size=(3, 3),
      pad='valid',
      nonlinearity=nonlinearities.softplus,
      name='conv4'
    )

    self.outputs = [conv_companion(conv5)]

    super(SimpleDiscriminator, self).__init__(self.outputs)

class StairsDiscriminator(Expression):
  def __init__(self, depth = 5, img_shape=(1, 128, 128), noise_sigma=1.0 / (2 ** 11)):
    self.input_layer = layers.InputLayer(
      shape=(None,) + img_shape,
      name='input'
    )

    self.outputs = []
    noise = layers.GaussianNoiseLayer(self.input_layer, sigma=noise_sigma, name='noise')

    for i in range(1, depth + 1):
      net = make_cnn(noise, depth=i, initial_filters=8, nonlinearity=nonlinearities.elu)
      net = conv_companion(net)

      self.outputs.append(net)

    super(StairsDiscriminator, self).__init__(self.outputs)

class DeeplySupervisedDiscriminator(Expression):
  def __init__(self, depth = 5, initial_filters=8, img_shape=(1, 128, 128), noise_sigma=1.0 / (2 ** 11)):
    self.outputs = []

    self.input_layer = layers.InputLayer(
      shape=(None,) + img_shape,
      name='input'
    )

    noise = layers.GaussianNoiseLayer(self.input_layer, sigma=noise_sigma, name='noise')

    self.outputs.append(conv_companion(noise, pool_function=T.mean))
    self.outputs.append(conv_companion(noise, pool_function=T.max))
    self.outputs.append(conv_companion(noise, pool_function=T.min))

    net = noise

    for i in range(depth):
      net = layers.Conv2DLayer(
        net,
        num_filters=initial_filters * (2 ** i),
        filter_size=(3, 3),
        pad='valid',
        nonlinearity=nonlinearities.softplus,
        name='conv%d' % (i + 1)
      )

      self.outputs.append(conv_companion(net))

      if i != depth - 1:
        net = layers.MaxPool2DLayer(
          net, pool_size=(2, 2),
          name='pool%d' % (i + 1)
        )

    super(DeeplySupervisedDiscriminator, self).__init__(self.outputs)