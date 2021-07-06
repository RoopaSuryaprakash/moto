import functools

import boto3
from botocore import handlers

from moto.motocore.handlers import CUSTOM_HANDLERS


class MyClass(object):
    def __init__(self, *args, **kwargs):
        super(MyClass, self).__init__(*args, **kwargs)
        self._register_custom_handlers()
        # Just to get PyCharm to shut up
        self.meta = getattr(self, "meta")

    def _register_custom_handlers(self):
        for spec in CUSTOM_HANDLERS:
            if len(spec) == 2:
                event_name, handler = spec
                self.meta.events.register(event_name, handler)
            else:
                event_name, handler, register_type = spec
                if register_type is handlers.REGISTER_FIRST:
                    self.meta.events.register_first(event_name, handler)
                elif register_type is handlers.REGISTER_LAST:
                    self.meta.events.register_last(event_name, handler)

    def test_request_dict(self, parsed_request, operation_model):
        service_id = self.meta.service_model.service_id.hyphenize()
        context = {"service": service_id, "region": self.meta.region_name}
        self.meta.events.emit(
            "request-after-parsing.{service_id}.{operation_name}".format(
                service_id=service_id, operation_name=operation_model.name
            ),
            parsed_request=parsed_request,
            operation_model=operation_model,
            context=context,
        )

        # api_params = first_non_none_response(responses, default=request_dict)
        # return api_params

    def test_result_dict(self, result_dict, operation_model):
        service_id = self.meta.service_model.service_id.hyphenize()
        # responses =
        self.meta.events.emit(
            "before-result-serialization.{service_id}.{operation_name}".format(
                service_id=service_id, operation_name=operation_model.name
            ),
            result_dict=result_dict,
            operation_model=operation_model,
        )

        # api_params = first_non_none_response(responses, default=request_dict)
        # return api_params

    def test_after_result(self, result, operation_model):
        service_id = self.meta.service_model.service_id.hyphenize()
        # responses =
        self.meta.events.emit(
            "backend-result-received.{service_id}.{operation_name}".format(
                service_id=service_id, operation_name=operation_model.name
            ),
            result=result,
            operation_model=operation_model,
        )

        # api_params = first_non_none_response(responses, default=request_dict)
        # return api_params


def add_custom_class(base_classes, **kwargs):
    base_classes.insert(0, MyClass)


@functools.lru_cache(maxsize=None)
def get_custom_client(service, **kwargs):
    session = boto3.Session()
    session.events.register("creating-client-class", add_custom_class)
    client = session.client(service, **kwargs)

    # Use our loader
    # TODO: We'll probably need to override/overwrite all the botocore client stuff
    # Like create a client creation process that utilizes what we can from botocore
    from moto.motocore.loaders import Loader
    from moto.motocore.model import ServiceModel

    client._loader = Loader()
    model = client._loader.load_service_model(
        client._service_model.service_name,
        "service-2",
        api_version=client._service_model.api_version,
    )
    client.meta._service_model = ServiceModel(model)

    # TODO: User our Parser/Serializer
    # Serializer might be more complicated because request could ask for JSON instead of XML

    return client
