from moto.motocore.loaders import _load_service_model
from moto.ec2 import ec2_backends
from moto.ec2._models.amis import Ami
from moto.motocore.serialize import create_serializer


def test_ami_serialization():
    model = _load_service_model("ec2")
    backend = ec2_backends["us-east-1"]
    ami = Ami(
        backend, ami_id="ami-1234", architecture="i386", virtualization_type="hvm",
    )
    operation_model = model.operation_model("DescribeImages")
    result_dict = {"Images": [ami, ami]}
    serializer = create_serializer("query")
    serializer.ALIASES.update({"Ami": "Image"})
    serialized = serializer.serialize_object(result_dict, operation_model)
    serialized = serializer.serialize_to_response(result_dict, operation_model)
    print(serialized)


# TODO:
# Test the various ways of getting an attribute
# ClassnameAttribute, camel, snake, etc.
# Should test that if the model wants a string we don't give it a list or whatever.
# Basically type checking the response model.
# https://github.com/spulec/moto/blob/master/moto/ec2/responses/launch_templates.py
