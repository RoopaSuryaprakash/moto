import six
from botocore import xform_name
from botocore.utils import parse_timestamp

DEFAULT_TIMESTAMP_PARSER = parse_timestamp
import json


class RequestParserFactory(object):
    def __init__(self):
        self._defaults = {}

    def set_parser_defaults(self, **kwargs):
        """Set default arguments when a parser instance is created.

        You can specify any kwargs that are allowed by a ResponseParser
        class.  There are currently two arguments:

            * timestamp_parser - A callable that can parse a timetsamp string
            * blob_parser - A callable that can parse a blob type

        """
        self._defaults.update(kwargs)

    def create_parser(self, protocol_name):
        parser_cls = PROTOCOL_PARSERS[protocol_name]
        return parser_cls(**self._defaults)


def create_parser(protocol):
    return RequestParserFactory().create_parser(protocol)


# noinspection PyUnusedLocal
class CloudFormationPropertiesParser(object):
    # This deserializes from a dict of properties, but
    # scalar value like 'db_subnet_group_name' might actually
    # be the backend db_subnet_group_entity, so we have to
    # pull from there if needed.

    # Not all CF properties map directly to API parameters...
    SHAPE_NAME_TO_CF_PROPERTY_MAP = {
        "DBParameterGroupFamily": "Family",
        "DBSecurityGroupDescription": "GroupDescription",
        "VpcSecurityGroupIds": "VPCSecurityGroups",
    }

    def __init__(self, convert_to_snake_case=True):
        self.convert_to_snake_case = convert_to_snake_case

    def parse(self, properties, shape):
        parsed = {}
        if shape is not None:
            parsed = self._parse_shape(shape, properties)
        return parsed

    def _parse_shape(self, shape, prop):
        handler = getattr(self, "_handle_%s" % shape.type_name, self._default_handle)
        return handler(shape, prop)

    def _handle_structure(self, shape, prop):
        parsed = {}
        members = shape.members
        for member_name in members:
            member_shape = members[member_name]
            prop_name = self._prop_key_name(member_name)
            prop_value = prop.get(prop_name)
            if prop_value is not None:
                parsed_key = self._parsed_key_name(member_name)
                parsed[parsed_key] = self._parse_shape(member_shape, prop_value)
        return parsed

    def _handle_list(self, shape, prop):
        parsed = []
        member_shape = shape.member
        for item in prop:
            parsed.append(self._parse_shape(member_shape, item))
        return parsed

    @staticmethod
    def _handle_boolean(shape, text):
        if text == "true":
            return True
        else:
            return False

    @staticmethod
    def _handle_integer(shape, text):
        return int(text)

    @staticmethod
    def _default_handle(shape, value):
        # If value is non-scalar, try to get the scalar from the object.
        if value and not isinstance(value, six.string_types):
            value = getattr(value, "resource_id", value)
        return value

    def _prop_key_name(self, member_name):
        return self.SHAPE_NAME_TO_CF_PROPERTY_MAP.get(member_name, member_name)

    def _parsed_key_name(self, member_name):
        key_name = member_name
        if self.convert_to_snake_case:
            key_name = xform_name(key_name)
        return key_name


class QueryStringParametersParser(object):
    def __init__(self, convert_to_snake_case=True):
        self.convert_to_snake_case = convert_to_snake_case

    def parse(self, query_params, shape):
        parsed = {}
        if shape is not None:
            parsed = self._parse_shape(shape, query_params)
        return parsed

    def _parse_shape(self, shape, query_params, prefix=""):
        handler = getattr(self, "_handle_%s" % shape.type_name, self._default_handle)
        return handler(shape, query_params, prefix=prefix)

    def _handle_structure(self, shape, query_params, prefix=""):
        parsed = {}
        members = shape.members
        for member_name in members:
            member_shape = members[member_name]
            member_prefix = self._get_serialized_name(member_shape, member_name)
            if prefix:
                member_prefix = "%s.%s" % (prefix, member_prefix)
            if self._has_member(query_params, member_prefix):
                parsed_key = self._parsed_key_name(member_name)
                parsed[parsed_key] = self._parse_shape(
                    member_shape, query_params, member_prefix
                )
        return parsed

    def _handle_list(self, shape, query_params, prefix=""):
        parsed = []
        member_shape = shape.member

        list_prefixes = []
        list_names = list({shape.member.serialization.get("name", "member"), "member"})
        for list_name in list_names:
            list_prefixes.append("%s.%s" % (prefix, list_name))

        for list_prefix in list_prefixes:
            i = 1
            while self._has_member(query_params, "%s.%s" % (list_prefix, i)):
                parsed.append(
                    self._parse_shape(
                        member_shape, query_params, "%s.%s" % (list_prefix, i)
                    )
                )
                i += 1
        return parsed

    def _handle_boolean(self, shape, query_params, prefix=""):
        value = self._default_handle(shape, query_params, prefix)
        if value.lower() == "true":
            return True
        else:
            return False

    def _handle_integer(self, shape, query_params, prefix=""):
        value = self._default_handle(shape, query_params, prefix)
        return int(value)

    def _default_handle(self, shape, query_params, prefix=""):
        # urlparse parses all querystring values into lists.
        return query_params.get(prefix)[0]

    def _get_serialized_name(self, shape, default_name):
        return shape.serialization.get("name", default_name)

    def _parsed_key_name(self, member_name):
        key_name = member_name
        if self.convert_to_snake_case:
            key_name = xform_name(key_name)
        return key_name

    def _has_member(self, value, member_prefix):
        return any(i for i in value if i.startswith(member_prefix))


class RequestParser(object):
    """Base class for response parsing.

    This class represents the interface that all ResponseParsers for the
    various protocols must implement.

    This class will take an HTTP response and a model shape and parse the
    HTTP response into a dictionary.

    There is a single public method exposed: ``parse``.  See the ``parse``
    docstring for more info.

    """

    DEFAULT_ENCODING = "utf-8"
    EVENT_STREAM_PARSER_CLS = None

    MAP_TYPE = dict

    def __init__(self, timestamp_parser=None, blob_parser=None):
        if timestamp_parser is None:
            timestamp_parser = DEFAULT_TIMESTAMP_PARSER
        self._timestamp_parser = timestamp_parser
        if blob_parser is None:
            blob_parser = self._default_blob_parser
        self._blob_parser = blob_parser
        self._event_stream_parser = None
        if self.EVENT_STREAM_PARSER_CLS is not None:
            self._event_stream_parser = self.EVENT_STREAM_PARSER_CLS(
                timestamp_parser, blob_parser
            )

    def _default_blob_parser(self, value):
        # Blobs are always returned as bytes type (this matters on python3).
        # We don't decode this to a str because it's entirely possible that the
        # blob contains binary data that actually can't be decoded.
        return base64.b64decode(value)

    def _parse_action(self, request_dict):
        return NotImplementedError()

    def parse(self, request_dict, service_model):
        """Parse the HTTP response given a shape.

        :param request_dict: The HTTP response dictionary.  This is a dictionary
            that represents the HTTP request.  The dictionary must have the
            following keys, ``body``, ``headers``.

        :param service_model: The model shape describing the expected output.
        :return: Returns a dictionary representing the parsed response
            described by the model.  In addition to the shape described from
            the model, each response will also have a ``ResponseMetadata``
            which contains metadata about the response, which contains at least
            two keys containing ``RequestId`` and ``HTTPStatusCode``.  Some
            responses may populate additional keys, but ``RequestId`` will
            always be present.

        """

        action = self._parse_action(request_dict)
        operation_model = service_model.operation_model(action)
        parsed = {}
        if operation_model.input_shape is not None:
            parsed = self._do_parse(request_dict, operation_model.input_shape)
        return parsed

    def _do_parse(self, request_dict, shape):
        raise NotImplementedError("%s._do_parse" % self.__class__.__name__)

    def _do_error_parse(self, response, shape):
        raise NotImplementedError("%s._do_error_parse" % self.__class__.__name__)

    def _parse_shape(self, shape, node):
        handler = getattr(self, "_handle_%s" % shape.type_name, self._default_handle)
        return handler(shape, node)

    def _handle_list(self, shape, node):
        # Enough implementations share list serialization that it's moved
        # up here in the base class.
        parsed = []
        member_shape = shape.member
        for item in node:
            parsed.append(self._parse_shape(member_shape, item))
        return parsed

    def _default_handle(self, shape, value):
        return value


class QueryParser(RequestParser):
    def parse(self, request_dict, service_model):
        """Parse the HTTP response given a shape.

        :param request_dict: The HTTP response dictionary.  This is a dictionary
            that represents the HTTP request.  The dictionary must have the
            following keys, ``body``, ``headers``.

        :param service_model: The model shape describing the expected output.
        :return: Returns a dictionary representing the parsed response
            described by the model.  In addition to the shape described from
            the model, each response will also have a ``ResponseMetadata``
            which contains metadata about the response, which contains at least
            two keys containing ``RequestId`` and ``HTTPStatusCode``.  Some
            responses may populate additional keys, but ``RequestId`` will
            always be present.

        """

        action = self._parse_action(request_dict)
        operation_model = service_model.operation_model(action)
        parsed = {"action": xform_name(action), "kwargs": {}}

        shape = operation_model.input_shape
        if shape is None:
            return parsed
        parsed["kwargs"] = self._do_parse(request_dict, operation_model.input_shape)
        return parsed

    def _parse_action(self, request_dict):
        action = None
        if request_dict["body"]:
            action = request_dict["body"].get("Action")
        if action is None:
            # Also try querystring.  It's not supposed to be here, but is for Moto server tests...
            if request_dict["query_string"]:
                action = request_dict["query_string"].get("Action")
        return action

    def _do_parse(self, request_dict, shape):
        parsed = {}
        if request_dict["body"]:
            parsed = self._parse_shape(shape, request_dict["body"])
        else:
            parsed = self._parse_shape(shape, request_dict["query_string"])
        return parsed

    def _parse_shape(self, shape, query_params, prefix=""):
        handler = getattr(self, "_handle_%s" % shape.type_name, self._default_handle)
        return handler(shape, query_params, prefix=prefix)

    def _handle_structure(self, shape, query_params, prefix=""):
        parsed = {}
        members = shape.members
        for member_name in members:
            member_shape = members[member_name]
            member_prefix = self._get_serialized_name(member_shape, member_name)
            if prefix:
                member_prefix = "%s.%s" % (prefix, member_prefix)
            if (
                self._has_member(query_params, member_prefix)
                or "default" in member_shape.metadata
            ):
                parsed_key = self._parsed_key_name(member_name)
                parsed[parsed_key] = self._parse_shape(
                    member_shape, query_params, member_prefix
                )
        return parsed

    def _handle_list(self, shape, query_params, prefix=""):
        parsed = []
        member_shape = shape.member

        # List members can be:
        # PrefixName.x
        # PrefixName.member.x
        # PrefixName.Name.x
        list_prefixes = [prefix]
        list_names = list({shape.member.serialization.get("name", "member"), "member"})
        for list_name in list_names:
            list_prefixes.append("%s.%s" % (prefix, list_name))

        for list_prefix in list_prefixes:
            i = 1
            while self._has_member(query_params, "%s.%s" % (list_prefix, i)):
                parsed.append(
                    self._parse_shape(
                        member_shape, query_params, "%s.%s" % (list_prefix, i)
                    )
                )
                i += 1
        return parsed

    def _handle_boolean(self, shape, query_params, prefix=""):
        value = self._default_handle(shape, query_params, prefix)
        if value is True or value is False:
            return value
        try:
            return value.lower() == "true"
        except AttributeError:
            pass
        return False

    def _handle_integer(self, shape, query_params, prefix=""):
        value = self._default_handle(shape, query_params, prefix)
        return int(value)

    def _default_handle(self, shape, query_params, prefix=""):
        # urlparse parses all querystring values into lists.
        return query_params.get(prefix, shape.metadata.get("default"))

    def _get_serialized_name(self, shape, default_name):
        return shape.serialization.get("name", default_name)

    def _parsed_key_name(self, member_name):
        key_name = member_name
        key_name = xform_name(key_name)
        return key_name

    def _has_member(self, value, member_prefix):
        return any(i for i in value if i.startswith(member_prefix))


class JSONParser(RequestParser):
    def _parse_action(self, request_dict):
        headers = request_dict["headers"]
        action = headers.get("X-Amz-Target", ".").split(".")[-1]
        return action

    def parse(self, request_dict, service_model):
        """Parse the HTTP response given a shape.

        :param request_dict: The HTTP response dictionary.  This is a dictionary
            that represents the HTTP request.  The dictionary must have the
            following keys, ``body``, ``headers``.

        :param service_model: The model shape describing the expected output.
        :return: Returns a dictionary representing the parsed response
            described by the model.  In addition to the shape described from
            the model, each response will also have a ``ResponseMetadata``
            which contains metadata about the response, which contains at least
            two keys containing ``RequestId`` and ``HTTPStatusCode``.  Some
            responses may populate additional keys, but ``RequestId`` will
            always be present.

        """

        action = self._parse_action(request_dict)
        operation_model = service_model.operation_model(action)
        parsed = {"action": xform_name(action), "kwargs": {}}

        shape = operation_model.input_shape
        if shape is None:
            return parsed
        parsed["kwargs"] = self._do_parse(request_dict, operation_model.input_shape)
        return parsed

    def _do_parse(self, request_dict, shape):
        parsed = {}
        data = json.loads(request_dict["body"])
        parsed = self._parse_shape(shape, data)
        return parsed

    def _parse_shape(self, shape, query_params, key=None):
        handler = getattr(self, "_handle_%s" % shape.type_name, self._default_handle)
        return handler(shape, query_params, key)

    def _handle_structure(self, shape, query_params, key):
        if key is not None:
            # If a key is provided, this is a result of a recursive
            # call so we need to add a new child dict as the value
            # of the passed in input dict.  We'll then add
            # all the structure members as key/vals in the new deserialized
            # dictionary we just created.
            # new_parsed = self.MAP_TYPE()
            # new_parsed[key] = new_parsed
            # parsed = new_parsed
            query_params = query_params[key]
        # else:
        parsed = {}
        members = shape.members
        for member_name in members:
            member_shape = members[member_name]
            location_name = member_name
            if "name" in member_shape.serialization:
                location_name = member_shape.serialization["name"]
            if self._has_member(query_params, location_name):
                parsed_key = self._parsed_key_name(member_name)
                parsed[parsed_key] = self._parse_shape(
                    member_shape, query_params, location_name
                )
        return parsed

    def _handle_list(self, shape, query_params, key=None):
        if key is not None:
            # If a key is provided, this is a result of a recursive
            # call so we need to add a new child dict as the value
            # of the passed in input dict.  We'll then add
            # all the structure members as key/vals in the new deserialized
            # dictionary we just created.
            # new_parsed = self.MAP_TYPE()
            # new_parsed[key] = new_parsed
            # parsed = new_parsed
            query_params = query_params[key]
        parsed = []

        for list_item in query_params:
            # The JSON list serialization is the only case where we aren't
            # setting a key on a dict.  We handle this by using
            # a __current__ key on a wrapper dict to serialize each
            # list item before appending it to the serialized list.
            parsed_item = self._parse_shape(shape.member, list_item)
            parsed.append(parsed_item)

        return parsed

    def _handle_boolean(self, shape, query_params, prefix=""):
        value = self._default_handle(shape, query_params, prefix)
        return True if value else False

    def _handle_integer(self, shape, query_params, prefix=""):
        value = self._default_handle(shape, query_params, prefix)
        return int(value)

    def _default_handle(self, shape, query_params, prefix=""):
        # urlparse parses all querystring values into lists.
        if prefix:
            value = query_params.get(prefix)
        else:
            value = query_params
        return value

    def _get_serialized_name(self, shape, default_name):
        return shape.serialization.get("name", default_name)

    def _parsed_key_name(self, member_name):
        key_name = member_name
        key_name = xform_name(key_name)
        return key_name

    def _has_member(self, value, member_prefix):
        return any(i for i in value if i.startswith(member_prefix))


class RestJSONParser(JSONParser):
    def _parse_rest_action(self, request_dict, service_model):
        # TODO: Find that ._expand_uri_template code in botocore and make this look like that
        path = request_dict["url_path"]
        for operation in service_model.operation_names:
            op = service_model.operation_model(operation)
            http = op.http
            if http["method"] != request_dict["method"]:
                continue
            path_parts = path.split("/")
            oppath_parts = http["requestUri"].split("/")
            if len(path_parts) != len(oppath_parts):
                continue
            for i in range(len(path_parts)):
                if oppath_parts[i].startswith("{") and oppath_parts[i].endswith("}"):
                    continue
                if path_parts[i] != oppath_parts[i]:
                    break
            else:
                return operation
        return None

    def _parse_uri_params(self, path, uri_template):
        path_parts = path.split("/")
        oppath_parts = uri_template.split("/")
        if len(path_parts) != len(oppath_parts):
            return {}
        params = {}
        for i in range(len(path_parts)):
            if oppath_parts[i].startswith("{") and oppath_parts[i].endswith("}"):
                key = oppath_parts[i][1:-1]
                params[key] = path_parts[i]
        return params

    def parse(self, request_dict, service_model):
        """Parse the HTTP response given a shape.

        :param request_dict: The HTTP response dictionary.  This is a dictionary
            that represents the HTTP request.  The dictionary must have the
            following keys, ``body``, ``headers``.

        :param service_model: The model shape describing the expected output.
        :return: Returns a dictionary representing the parsed response
            described by the model.  In addition to the shape described from
            the model, each response will also have a ``ResponseMetadata``
            which contains metadata about the response, which contains at least
            two keys containing ``RequestId`` and ``HTTPStatusCode``.  Some
            responses may populate additional keys, but ``RequestId`` will
            always be present.

        """

        action = self._parse_rest_action(request_dict, service_model)
        operation_model = service_model.operation_model(action)
        parsed = {"action": xform_name(action), "kwargs": {}}
        data = {}
        data.update(
            **self._parse_uri_params(
                request_dict["url_path"], operation_model.http["requestUri"]
            )
        )
        data.update(**request_dict["query_string"])
        if request_dict["body"]:
            data.update(**json.loads(request_dict["body"]))
        shape = operation_model.input_shape
        if shape is None:
            return parsed
        parsed["kwargs"] = self._do_parse(data, operation_model.input_shape)
        return parsed

    def _do_parse(self, request_dict, shape):
        parsed = {}
        parsed = self._parse_shape(shape, request_dict)
        return parsed


PROTOCOL_PARSERS = {
    #'ec2': EC2QueryParser,
    "query": QueryParser,
    "json": JSONParser,
    "rest-json": RestJSONParser,
    #  'rest-xml': RestXMLParser,
}
