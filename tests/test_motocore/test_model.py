import unittest

from moto.motocore import model


class TestOperationModelFromService(unittest.TestCase):
    def setUp(self):
        self.model = {
            "metadata": {"protocol": "query", "endpointPrefix": "foo"},
            "documentation": "",
            "operations": {
                "OperationName": {
                    "http": {"method": "POST", "requestUri": "/"},
                    "name": "OperationName",
                    "input": {"shape": "OperationNameRequest"},
                    "output": {"shape": "OperationNameResponse"},
                    "errors": [{"shape": "NoSuchResourceException"}],
                    "documentation": "Docs for OperationName",
                    "authtype": "v4",
                },
                "OperationTwo": {
                    "http": {"method": "POST", "requestUri": "/"},
                    "name": "OperationTwo",
                    "input": {"shape": "OperationNameRequest"},
                    "output": {"shape": "OperationNameResponse"},
                    "errors": [{"shape": "NoSuchResourceException"}],
                    "documentation": "Docs for OperationTwo",
                },
            },
            "shapes": {
                "OperationNameRequest": {
                    "type": "structure",
                    "members": {
                        "Arg1": {"shape": "stringType"},
                        "Arg2": {"shape": "stringType", "default": "arg_default"},
                    },
                },
                "OperationNameResponse": {
                    "type": "structure",
                    "members": {"String": {"shape": "stringType"}},
                },
                "NoSuchResourceException": {"type": "structure", "members": {}},
                "stringType": {"type": "string"},
            },
        }
        self.service_model = model.ServiceModel(self.model)

    def test_operation_input_model_has_moto_metadata(self):
        operation = self.service_model.operation_model("OperationName")
        shape = operation.input_shape
        self.assertEqual(shape.members["Arg2"].metadata["default"], "arg_default")


class TestShapeResolver(unittest.TestCase):
    def test_shape_moto_metadata_default(self):
        shapes = {
            "ChangePasswordRequest": {
                "type": "structure",
                "required": ["OldPassword", "NewPassword"],
                "members": {
                    "OldPassword": {"shape": "passwordType", "default": 50},
                    "NewPassword": {"shape": "passwordType"},
                },
            },
            "passwordType": {"type": "string", "default": 100},
        }
        resolver = model.ShapeResolver(shapes)
        shape = resolver.get_shape_by_name("ChangePasswordRequest")
        member = shape.members["OldPassword"]
        self.assertEqual(member.metadata["default"], 50)
        member = shape.members["NewPassword"]
        self.assertEqual(member.metadata["default"], 100)
