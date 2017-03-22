from keras.models import Sequential
from keras.layers.core import (Activation, Dense)
from keras.optimizers import Adam

import keras.layers as kl
import keras.initializers as ki
import keras.regularizers as kr

# concise modules
from concise import initializers as ci
from concise import layers as cl
from concise import activations as ca
from concise.utils import PWM


# ### 'Original' Concise architecture

# Splines:
# - `spline_score = X_spline %*% spline_weights`
# - Transform:
#   - `exp(spline_score)`
#   - `spline_score + 1`

# Linear features:
# - `lm_feat = X_feat %*% feature_weights`

# Model:
# - conv2d, `padding = "valid", w = motif_base_weights`
# - activation: exp or relu, bias = motif_bias
# - elementwise_multiply: `hidden * spline_score`
# - pooling: max, sum or mean (accross the whole model)
# - Optionally: multiply by non-linear scaling factor (model fitting)
# - `pool_layer %*% motif_weights + X_feat %*% feature_weights + final_bias`
# - loss: mse
# - optimizer: Adam, optionally l-BFGS

# Regularization:
# - motif_base_weights, L1: motif_lamb
# - motif_weights, L1: lambd
# - spline_weights:
#   - `diag(t(spline_weights) %*% S %*% spline_weights)`, L2_mean: spline_lamb
#   - spline_weights, L2 / n_spline_tracks: spline_param_lamb
# convolution model

def concise_model(pooling_layer="sum",  # 'sum', 'max' or 'mean'
                  nonlinearity="relu",  # 'relu' or 'exp'
                  motif_length=9,
                  n_motifs=6,           # number of filters
                  step_size=0.01,
                  num_tasks=1,          # multi-task learning - 'trans'
                  n_covariates=0,
                  seq_length=100,       # pre-defined sequence length
                  # splines
                  n_splines=None,
                  share_splines=False,  # should the positional bias be shared across motifs
                  spline_exp=False,     # use the exponential function
                  # regularization
                  lamb=1e-5,            # overall motif coefficient regularization
                  motif_lamb=1e-5,
                  spline_lamb=1e-5,
                  spline_param_lamb=1e-5,
                  # initialization
                  init_motifs=None,     # motifs to intialize
                  init_motif_bias=0,
                  init_sd_motif=1e-2,
                  init_sd_w=1e-3,       # initial weight scale of feature w or motif w
                  **kwargs):            # unused params

    # initialize conv kernels to known motif pwm's
    if init_motifs:
        # TODO - initialization is not the same as for Concise class
        pwm_list = [PWM.from_consensus(motif) for motif in init_motifs]
        kernel_initializer = ci.PWMKernelInitializer(pwm_list, stddev=init_sd_motif)
        bias_initializer = ci.PWMBiasInitializer(pwm_list, kernel_size=motif_length)
    else:
        # kernel_initializer = "glorot_uniform"
        kernel_initializer = ki.RandomNormal(stddev=init_sd_motif)
        bias_initializer = ki.Constant(value=init_motif_bias)

    if nonlinearity is "exp":
        activation = ca.exponential
    else:
        activation = nonlinearity  # supports 'relu' out-of-the-box

    # define the model
    # ----------------
    model = Sequential()
    # convolution
    model.add(kl.Conv1D(filters=n_motifs, kernel_size=motif_length,
                        kernel_regularizer=kr.l1(l=motif_lamb),  # Regularization
                        activation=activation,
                        kernel_initializer=kernel_initializer,
                        bias_initializer=bias_initializer,
                        batch_input_shape=(None, seq_length, 4),
                        )
              )
    # optional positional effect
    if n_splines:
        model.add(cl.GAMSmooth(n_bases=n_splines,
                               share_splines=share_splines,
                               spline_exp=spline_exp,
                               l2_smooth=spline_lamb,
                               l2=spline_param_lamb,
                               )
                  )
    # pooling layer
    if pooling_layer is "max":
        model.add(kl.pooling.GlobalMaxPooling1D())
    elif pooling_layer is "mean":
        model.add(kl.pooling.GlobalAveragePooling1D())
    elif pooling_layer is "sum":
        model.add(cl.GlobalSumPooling1D())
    else:
        raise ValueError("pooling_layer can only be 'sum', 'mean' or 'max'.")

    # -----
    # add covariates
    if n_covariates:
        linear_model = Sequential()
        linear_model.add(Activation("linear", input_shape=(n_covariates, )))
        merged = kl.Merge([model, linear_model], mode='concat')

        final_model = Sequential()
        final_model.add(merged)
    else:
        final_model = model
    # -----

    final_model.add(Dense(units=num_tasks,
                          kernel_regularizer=kr.l1(lamb),
                          kernel_initializer=ki.RandomNormal(stddev=init_sd_w)
                          ))

    model.compile(optimizer=Adam(lr=step_size), loss="mse", metrics=["mse"])

    return model

# See
    # TODO - callback?
    # keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=0, patience=early_stop_patience, verbose=0, mode='auto')
    # keras.callbacks.LearningRateScheduler(schedule)

# TODO - test that the exponential layer is serialized successfully
