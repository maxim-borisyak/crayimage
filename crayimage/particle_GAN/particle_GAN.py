import numpy as np
import theano
import theano.tensor as T

from lasagne import *
from .. import nn

__all__ = [
  'ParticleGAN'
]

class ParticleGAN(object):
  def __init__(self, background_net, particle_net, discriminator,
               mc_batch_layout, real_batch_layout, real_events_per_bin,
               event_rate_init=6.0, losses_coefs=None,
               geant_normalization=0.2, real_normalization=1024.0,
               event_rate_bounds=(1e-3, 64),
               minimal_loss_trick=False
               ):
    self.noise_generator = background_net
    self.particle_generator = particle_net
    self.discriminator = discriminator

    X_geant_raw = T.ftensor4('Composition of GEANT tracks')
    self.X_geant_raw = X_geant_raw
    X_geant = X_geant_raw / geant_normalization

    X_real_raw = T.tensor4('real samples', dtype='uint16')
    self.X_real_raw = X_real_raw
    X_real = X_real_raw / real_normalization

    # from theano.sandbox.cuda.rng_curand import CURAND_RandomStreams as RandomStreams
    from theano.sandbox.rng_mrg import MRG_RandomStreams as RandomStreams
    srng = RandomStreams(seed=11223344)

    X_noise = srng.uniform(
      low=0.0, high=1.0,
      size=(X_geant_raw.shape[0],) + background_net.input_shape,
      ndim=4, dtype='float32'
    )

    self.X_noise = X_noise

    X_background = layers.get_output(background_net.net, inputs={background_net.input_noise: X_noise})
    self.X_background = X_background

    X_pseudo = layers.get_output(particle_net.net, inputs={
      particle_net.input_background: X_background,
      particle_net.input_geant: X_geant
    })
    self.X_pseudo = X_pseudo

    self.probas_pseudo = layers.get_output(discriminator.outputs, inputs={
      discriminator.input_layer: X_pseudo
    })

    self.probas_real = layers.get_output(discriminator.outputs, inputs={
      discriminator.input_layer: X_real
    })

    from math import factorial

    self.mc_n_tracks = theano.shared(
      np.array(
        nn.join([[i] * n for i, n in enumerate(mc_batch_layout)]),
        dtype='float32'
      ),
      name='n_tracks'
    )

    # coefficient to count for different number of events
    # in each category
    self.mc_prior_weigth = theano.shared(
      np.array(
        nn.join([[1.0 / n / factorial(i)] * n for i, n in enumerate(mc_batch_layout)]),
        dtype='float32'
      ),
      name='prior_weight'
    )

    self.mc_event_rate = theano.shared(
      np.float32(event_rate_init), name='mc event rate'
    )

    self.mc_weights = T.exp(T.log(self.mc_event_rate) * self.mc_n_tracks) * T.exp(-self.mc_event_rate) * self.mc_prior_weigth

    self.real_bin_piors = real_events_per_bin * 1.0 / np.sum(real_events_per_bin)

    self.real_weights = theano.shared(
      np.array(
        nn.join([[self.real_bin_piors[i] / n] * n for i, n in enumerate(real_batch_layout)]),
        dtype='float32'
      )
    )

    self.losses_pseudo = [
      -T.sum(self.mc_weights * T.log(1 - p_pseudo)) / T.sum(self.mc_weights) for p_pseudo in self.probas_pseudo
     ]

    self.losses_real = [
      -T.sum(self.real_weights * T.log(p_real)) / T.sum(self.real_weights) for p_real in self.probas_real
    ]

    self.reg_background_net = regularization.regularize_network_params(background_net.net, regularization.l2)
    self.reg_particle_net = regularization.regularize_network_params(particle_net.net, regularization.l2)

    self.reg_discriminator = nn.join([
      T.sum(param ** 2)
      for param in layers.get_all_params(discriminator.outputs, regularizable=True)
    ])

    if losses_coefs is None:
      losses_coefs = np.ones(shape=len(self.losses_pseudo), dtype='float32')

    losses_coefs /= np.sum(losses_coefs, dtype='float32')

    self.loss_pseudo = nn.joinc(self.losses_pseudo, losses_coefs)
    self.loss_real = nn.joinc(self.losses_real, losses_coefs)

    self.pure_loss_discriminator = (self.loss_pseudo + self.loss_real) / 2

    self.loss_discriminator = self.pure_loss_discriminator + 1.0e-6 * self.reg_discriminator

    if minimal_loss_trick:
      self.pure_loss_generator = -nn.joinc(self.losses_pseudo, nn.softmin(self.losses_pseudo, alpha=2.0))
    else:
      self.pure_loss_generator = -self.loss_pseudo

    self.reg_event_rate = 1.0e-3 * nn.log_barrier(self.mc_event_rate, event_rate_bounds)

    self.loss_generator = nn.join([
      self.pure_loss_generator,
      1.0e-5 * (self.reg_particle_net + self.reg_background_net),
      self.reg_event_rate
    ])

    self.params_background_net = layers.get_all_params(background_net.net, trainable=True)
    self.params_pacticle_net = layers.get_all_params(particle_net.net, trainable=True)
    self.params_generator = self.params_background_net + self.params_pacticle_net + [self.mc_event_rate]

    self.params_discriminator = layers.get_all_params(discriminator.outputs, trainable=True)