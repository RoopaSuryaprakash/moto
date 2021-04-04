"""Module for loading various model files.

This module provides the classes that are used to load models used
by botocore.  This can include:

    * Service models (e.g. the model for EC2, S3, DynamoDB, etc.)
    * Service model extras which customize the service models
    * Other models associated with a service (pagination, waiters)
    * Non service-specific config (Endpoint data, retry config)

Loading a module is broken down into several steps:

    * Determining the path to load
    * Search the data_path for files to load
    * The mechanics of loading the file
    * Searching for extras and applying them to the loaded file

The last item is used so that other faster loading mechanism
besides the default JSON loader can be used.

The Search Path
===============

Similar to how the PATH environment variable is to finding executables
and the PYTHONPATH environment variable is to finding python modules
to import, the botocore loaders have the concept of a data path exposed
through AWS_DATA_PATH.

This enables end users to provide additional search paths where we
will attempt to load models outside of the models we ship with
botocore.  When you create a ``Loader``, there are two paths
automatically added to the model search path:

    * <botocore root>/data/
    * ~/.aws/models

The first value is the path where all the model files shipped with
botocore are located.

The second path is so that users can just drop new model files in
``~/.aws/models`` without having to mess around with the AWS_DATA_PATH.

The AWS_DATA_PATH using the platform specific path separator to
separate entries (typically ``:`` on linux and ``;`` on windows).


Directory Layout
================

The Loader expects a particular directory layout.  In order for any
directory specified in AWS_DATA_PATH to be considered, it must have
this structure for service models::

    <root>
      |
      |-- servicename1
      |   |-- 2012-10-25
      |       |-- service-2.json
      |-- ec2
      |   |-- 2014-01-01
      |   |   |-- paginators-1.json
      |   |   |-- service-2.json
      |   |   |-- waiters-2.json
      |   |-- 2015-03-01
      |       |-- paginators-1.json
      |       |-- service-2.json
      |       |-- waiters-2.json
      |       |-- service-2.sdk-extras.json


That is:

    * The root directory contains sub directories that are the name
      of the services.
    * Within each service directory, there's a sub directory for each
      available API version.
    * Within each API version, there are model specific files, including
      (but not limited to): service-2.json, waiters-2.json, paginators-1.json

The ``-1`` and ``-2`` suffix at the end of the model files denote which version
schema is used within the model.  Even though this information is available in
the ``version`` key within the model, this version is also part of the filename
so that code does not need to load the JSON model in order to determine which
version to use.

The ``sdk-extras`` and similar files represent extra data that needs to be
applied to the model after it is loaded. Data in these files might represent
information that doesn't quite fit in the original models, but is still needed
for the sdk. For instance, additional operation parameters might be added here
which don't represent the actual service api.
"""
import logging
import os

from botocore.loaders import Loader as BotocoreLoader

from moto import MOTO_ROOT

logger = logging.getLogger(__name__)


cache = {}


def _load_service_model(service_name, api_version=None):
    from moto.motocore.model import ServiceModel

    if service_name in cache and api_version is not None:
        if api_version in cache[service_name]:
            return cache[service_name][api_version]
    loader = Loader()
    json_model = loader.load_service_model(
        service_name, "service-2", api_version=api_version
    )
    service_model = ServiceModel(json_model, service_name=service_name)
    if service_name not in cache:
        cache[service_name] = {}
    if api_version is not None:
        cache[service_name][api_version] = service_model
    return service_model


class Loader(BotocoreLoader):
    """Find and load data models.

    This class will handle searching for and loading data models.

    The main method used here is ``load_service_model``, which is a
    convenience method over ``load_data`` and ``determine_latest_version``.

    """

    # The included models in botocore/data/ that we ship with botocore.
    # BUILTIN_DATA_PATH = os.path.join(BOTOCORE_ROOT, 'data')

    # For convenience we automatically add ~/.aws/models to the data path.
    # We can use this to merge in our moto model extras
    CUSTOMER_DATA_PATH = os.path.join(MOTO_ROOT, "data")
    BUILTIN_EXTRAS_TYPES = ["moto"]
