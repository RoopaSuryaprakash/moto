"""Abstractions to interact with service models."""

from botocore.model import ServiceModel as BotocoreServiceModel
from botocore.model import ShapeResolver as BotocoreShapeResolver

MOTO_METADATA_ATTRS = ["default", "default_result_key"]


class ServiceModel(BotocoreServiceModel):
    """

    :ivar service_description: The parsed service description dictionary.

    """

    def __init__(self, service_description, service_name=None):
        """

        :type service_description: dict
        :param service_description: The service description model.  This value
            is obtained from a botocore.loader.Loader, or from directly loading
            the file yourself::

                service_description = json.load(
                    open('/path/to/service-description-model.json'))
                model = ServiceModel(service_description)

        :type service_name: str
        :param service_name: The name of the service.  Normally this is
            the endpoint prefix defined in the service_description.  However,
            you can override this value to provide a more convenient name.
            This is done in a few places in botocore (ses instead of email,
            emr instead of elasticmapreduce).  If this value is not provided,
            it will default to the endpointPrefix defined in the model.

        """
        super(ServiceModel, self).__init__(service_description, service_name)
        # Use our shape resolver
        self._shape_resolver = ShapeResolver(service_description.get("shapes", {}))


class ShapeResolver(BotocoreShapeResolver):
    """Resolves shape references."""

    def get_shape_by_name(self, shape_name, member_traits=None):
        result = super().get_shape_by_name(shape_name, member_traits)
        # Patch each shape to use our additional attrs
        # At first I was just adding and it kept adding default over and over...
        result.METADATA_ATTRS = list(
            set(result.METADATA_ATTRS) | set(MOTO_METADATA_ATTRS)
        )
        return result
