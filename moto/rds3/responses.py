from __future__ import unicode_literals

from moto.core.responses import BaseResponse


class RDSResponse(BaseResponse):
    @classmethod
    def dispatch(cls, *args, **kwargs):
        from moto.motocore.awsrequest import convert_to_request_dict

        return convert_to_request_dict(*args)
