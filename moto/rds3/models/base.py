import datetime

from moto.core import BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds


class BaseRDSModel(BaseModel):

    resource_type = None

    def __init__(self, backend):
        self.backend = backend
        self.created = iso_8601_datetime_with_milliseconds(datetime.datetime.now())

    @property
    def resource_id(self):
        raise NotImplementedError("Subclasses must implement resource_id property.")

    @property
    def region(self):
        return self.backend.region_name

    @property
    def account_id(self):
        return self.backend.account_id

    @property
    def arn(self):
        return "arn:aws:rds:{region}:{account_id}:{resource_type}:{resource_id}".format(
            region=self.region,
            account_id=self.account_id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
        )

    def get_regional_backend(self, region):
        from . import rds3_backends

        return rds3_backends[self.account_id][region]

    def get_regional_ec2_backend(self, region):
        from moto.ec2.models import ec2_backends

        return ec2_backends[self.account_id][region]
