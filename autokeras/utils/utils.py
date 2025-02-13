# Copyright 2020 The AutoKeras Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import warnings

import keras_tuner
import tensorflow as tf
from packaging.version import parse
from tensorflow import nest


def validate_num_inputs(inputs, num):
    inputs = nest.flatten(inputs)
    if not len(inputs) == num:
        raise ValueError(
            "Expected {num} elements in the inputs list "
            "but received {len} inputs.".format(num=num, len=len(inputs))
        )


def to_snake_case(name):
    intermediate = re.sub("(.)([A-Z][a-z0-9]+)", r"\1_\2", name)
    insecure = re.sub("([a-z])([A-Z])", r"\1_\2", intermediate).lower()
    return insecure


def check_tf_version() -> None:
    if parse(tf.__version__) < parse("2.7.0"):
        warnings.warn(
            "The Tensorflow package version needs to be at least 2.7.0 \n"
            "for AutoKeras to run. Currently, your TensorFlow version is \n"
            f"{tf.__version__}. Please upgrade with \n"
            "`$ pip install --upgrade tensorflow`. \n"
            "You can use `pip freeze` to check afterwards that everything is ok.",
            ImportWarning,
        )


def check_kt_version() -> None:
    if parse(keras_tuner.__version__) < parse("1.1.0"):
        warnings.warn(
            "The Keras Tuner package version needs to be at least 1.1.0 \n"
            "for AutoKeras to run. Currently, your Keras Tuner version is \n"
            f"{keras_tuner.__version__}. Please upgrade with \n"
            "`$ pip install --upgrade keras-tuner`. \n"
            "You can use `pip freeze` to check afterwards that everything is ok.",
            ImportWarning,
        )


def contain_instance(instance_list, instance_type):
    return any([isinstance(instance, instance_type) for instance in instance_list])


def evaluate_with_adaptive_batch_size(model, batch_size, verbose=1, **fit_kwargs):
    return run_with_adaptive_batch_size(
        batch_size,
        lambda x, validation_data, **kwargs: model.evaluate(
            x, verbose=verbose, **kwargs
        ),
        **fit_kwargs,
    )


def predict_with_adaptive_batch_size(model, batch_size, verbose=1, **fit_kwargs):
    return run_with_adaptive_batch_size(
        batch_size,
        lambda x, validation_data, **kwargs: model.predict(
            x, verbose=verbose, **kwargs
        ),
        **fit_kwargs,
    )


def fit_with_adaptive_batch_size(model, batch_size, **fit_kwargs):
    history = run_with_adaptive_batch_size(
        batch_size, lambda **kwargs: model.fit(**kwargs), **fit_kwargs
    )
    return model, history


def run_with_adaptive_batch_size(batch_size, func, **fit_kwargs):
    x = fit_kwargs.pop("x")
    validation_data = None
    if "validation_data" in fit_kwargs:
        validation_data = fit_kwargs.pop("validation_data")
    while batch_size > 0:
        try:
            history = func(x=x, validation_data=validation_data, **fit_kwargs)
            break
        except tf.errors.ResourceExhaustedError as e:
            if batch_size == 1:
                raise e
            batch_size //= 2
            print(
                "Not enough memory, reduce batch size to {batch_size}.".format(
                    batch_size=batch_size
                )
            )
            x = x.unbatch().batch(batch_size)
            if validation_data is not None:
                validation_data = validation_data.unbatch().batch(batch_size)
    return history


def get_hyperparameter(value, hp, dtype):
    if value is None:
        return hp
    return value


def add_to_hp(hp, hps, name=None):
    """Add the HyperParameter (self) to the HyperParameters.

    # Arguments
        hp: keras_tuner.HyperParameters.
        name: String. If left unspecified, the hp name is used.
    """
    if not isinstance(hp, keras_tuner.engine.hyperparameters.HyperParameter):
        return hp
    kwargs = hp.get_config()
    if name is None:
        name = hp.name
    kwargs.pop("conditions")
    kwargs.pop("name")
    class_name = hp.__class__.__name__
    func = getattr(hps, class_name)
    return func(name=name, **kwargs)


def serialize_keras_object(obj):
    if hasattr(tf.keras.utils, "legacy"):
        return tf.keras.utils.legacy.serialize_keras_object(obj)  # pragma: no cover
    else:
        return tf.keras.utils.serialize_keras_object(obj)


def deserialize_keras_object(
    config, module_objects=None, custom_objects=None, printable_module_name=None
):
    if hasattr(tf.keras.utils, "legacy"):
        return tf.keras.utils.legacy.deserialize_keras_object(  # pragma: no cover
            config, custom_objects, module_objects, printable_module_name
        )
    else:
        return tf.keras.utils.deserialize_keras_object(
            config, custom_objects, module_objects, printable_module_name
        )
