import functools

import six
from botocore.awsrequest import HeadersDict
from botocore.session import get_session
from botocore.utils import get_encoding_from_headers
from six.moves.urllib.parse import parse_qsl, urlparse
from werkzeug.http import parse_options_header

from moto.core.utils import get_random_message_id
from moto.motocore.client import get_custom_client
from moto.motocore.regions import EndpointResolver

DEFAULT_ENCODING = "utf-8"


def convert_to_request_dict(request, full_url, headers):
    parsed = urlparse(full_url)
    request_dict = {
        "hostname": parsed.hostname,
        "url_path": parsed.path,  # getattr(request, 'path', '/'),
        "query_string": parsed.query,  # getattr(request, 'query_string', ''),
        "method": getattr(request, "method", "GET"),
        "headers": getattr(request, "headers", headers),
        "body": getattr(request, "body", b""),
        "url": getattr(request, "url", full_url),
    }
    normalize_request_dict(request_dict)
    request_dict["context"] = aws_context_from_request(request_dict)
    # TODO: Need to get this dict into a class like they do in botocore so I don't have to do dict notation...
    return request_dict_to_parsed(request_dict)
    # return request_dict


def aws_context_from_headers(headers):
    # This needs to be broken out into proper auth and signer modules...
    # check werkzeug.http.parse_authorization_header for ideas
    # NOTE: the region we get from this is the credentialScope region in the endpoint data
    # For example: IAM region is `aws-global` but the credentialScope for the header is `us-east-1`
    # This is a special case, but we'll need to pick which one to return (or, alternatively, have
    # the IAM backends reference the same backend object for `aws-global` and `us-east-1`
    value = headers.get("Authorization")
    if not value:
        return
    try:
        auth_type, auth_info = value.split(" ", 1)
        auth_type = auth_type.lower()
    except ValueError:
        return
    if auth_type == "aws4-hmac-sha256":
        options = auth_info.split(",")
        details = {k: v for option in options for k, v in [option.split("=", 1)]}
        credential = details.get("Credential")
        if credential:
            _, __, region, service, _____ = credential.split("/")
            return {"region": region, "service": service}


@functools.lru_cache(maxsize=None)
def get_endpoint_data():
    session = get_session()
    loader = session.get_component("data_loader")
    endpoint_data = loader.load_data("endpoints")
    return endpoint_data


def aws_context_from_request(req):
    ctx = {"api_version": None}
    auth_ctx = aws_context_from_headers(req["headers"])
    if auth_ctx:
        ctx.update(**auth_ctx)
    endpoint_data = get_endpoint_data()
    deconstructor = EndpointResolver(endpoint_data)
    result = deconstructor.deconstruct_endpoint(req["hostname"])
    ctx.update(**result)
    if isinstance(req["body"], dict):
        ctx["api_version"] = req["body"].get("Version")
    # TODO: I don't know if we need this... or maybe we need the inverse...
    # ctx["service"] = SERVICE_ALIASES.get(ctx["service"], ctx["service"])
    return ctx


def get_protocol_from_headers(headers):
    protocol = None
    content_type = headers.get("content-type", "")
    if content_type.startswith("application/x-www-form-urlencoded"):
        protocol = "query"
    elif content_type.startswith("application/x-amz-json"):
        protocol = "json"
    return protocol


def get_default_result_key(shape):
    # TODO: This is still a giant hack, but I needed to get this out of the serializer
    # We have multiple option here:
    # Add to default_result_key to metadata for output shapes (very time-consuming)
    # Have the responses classes get the data from the backend and wrap with the
    # appropriate key (hate to add all that boilerplate just for that
    # Have the backend methods return the data wrapped in a key (don't like that,
    # backend methods should be pure...
    # Bleh... I don't know...
    if shape is None:
        return None
    key = shape.metadata.get("default_result_key", "result")
    possible_names = list(shape.members.keys())
    for token_field in ["Marker", "NextToken"]:
        if token_field in possible_names:
            possible_names.remove(token_field)
    if len(possible_names) == 1:
        key = possible_names[0]
    return key


def request_dict_to_parsed(request_dict):
    ctx = request_dict["context"]
    # TODO: Not sure when/where to generate this
    ctx["request_id"] = get_random_message_id()
    client = get_custom_client(
        ctx["service"],
        region_name=ctx["region"],
        api_version=ctx["api_version"],
    )

    # The former is for boto because they use Query in places where Boto3 uses json or rest-json, etc.
    protocol = (
        get_protocol_from_headers(request_dict["headers"])
        or client.meta.service_model.protocol
    )

    from moto.motocore.parsers import RequestParserFactory

    parser = RequestParserFactory().create_parser(protocol)
    try:
        result = parser.parse(request_dict, client.meta.service_model)
    except Exception as e:
        print(e)

    # backend_action --- hur hur hur
    params = result["kwargs"]
    backend_action = result["action"]
    api_action = client.meta.method_to_api_mapping[backend_action]
    operation_model = client.meta.service_model.operation_model(api_action)

    # Need to really nail down interface for parser "result"
    # action/kwargs?  action/params?  What else?
    # print(result)
    client.test_request_dict(result, operation_model)

    from moto.backends import get_backend

    backend = get_backend(ctx["service"])[ctx["region"]]
    if not hasattr(backend, backend_action):
        raise NotImplementedError(
            "The {service_name}.{operation_name} operation has not been mocked in Moto.".format(
                operation_name=api_action,
                service_name=client.meta.service_model.service_id.hyphenize(),
            )
        )

    try:
        # from moto.motocore.compat import inspect_getargspec

        # TODO: I feel like we should check the response object first and call that
        # method if it exists, otherwise call the backend method.
        # This would allow the backend to just, say, return a list of objects and
        # the response method to wrap in with the right key, e.g. DBClusters
        method = getattr(backend, backend_action)
        # TODO: Only pass parameters that match the call signature; pass all if kwargs is present.
        # param_spec = inspect.signature(method)
        # arg_spec = inspect_getargspec(method)
        # This is super cool because we can use it to only send params
        # that the method accepts and we can also detect VAR_KEYWORD to
        # if we can just pass everything.
        # print(param_spec)
        result = None
        if method:
            result = getattr(backend, backend_action)(**params)

        # client.test_after_result(result, operation_model)

        # TODO: We should actually make a paginate decorator and then just
        # call the method decorated if can_paginate is True
        if client.can_paginate(backend_action) and ctx["service"] == "rds":
            result, marker = _paginate_response(result, params)
        else:
            marker = None

        if isinstance(result, dict):
            result_dict = result
        else:
            result_key = get_default_result_key(operation_model.output_shape)
            result_dict = {result_key: result}
        if marker:
            result_dict["marker"] = marker

        new_result = client.test_result_dict(result_dict, operation_model)
        if new_result is not None:
            result_dict = new_result

    except Exception as e:  # TODO: catch on generic base AWSError or AWSException
        result_dict = e

    from moto.motocore.serialize import create_serializer

    # TODO: Fix this HACK
    if "ContentType" in request_dict["body"]:
        protocol = "{}-{}".format(protocol, request_dict["body"]["ContentType"].lower())
    serializer = create_serializer(protocol)
    response = serializer.serialize_to_response(result_dict, operation_model)

    return response["status_code"], response["headers"], response["body"]


# This was pulled from RDS3 but needs to be generified and moved to its own module
MAX_RECORDS = 100


def _paginate_response(resources, parameters):
    from moto.rds.exceptions import InvalidParameterValue

    marker = parameters.get("marker")
    page_size = parameters.get("max_records", MAX_RECORDS)
    # TODO: This validation should be done during parameter parsing
    if page_size < 20 or page_size > 100:
        msg = "Invalid value {} for MaxRecords. Must be between 20 and 100".format(
            page_size
        )
        raise InvalidParameterValue(msg)
    all_resources = list(resources)
    all_ids = [resource.resource_id for resource in all_resources]
    if marker:
        start = all_ids.index(marker) + 1
    else:
        start = 0
    paginated_resources = all_resources[start : start + page_size]
    next_marker = None
    if len(all_resources) > start + page_size:
        next_marker = paginated_resources[-1].resource_id
    return paginated_resources, next_marker


# Class NormalizeRequest  RequestNormalizer should be the opposite of the preparer classes in botocore
# basically, instead of converting things to bytes or url_encoding, we do the opposite


def normalize_request_dict(request_dict, context=None):
    """
    This method normalizes a request dict to be created into an
    AWSRequestObject. This normalizes the request dict by decoding
    the querystring and body

    :type request_dict: dict
    :param request_dict:  The request dict (created from the
        ``serialize`` module).

    :type user_agent: string
    :param user_agent: The user agent to use for this request.

    :type endpoint_url: string
    :param endpoint_url: The full endpoint url, which contains at least
        the scheme, the hostname, and optionally any path components.
    """

    def convert_params_to_dict(data, enc):
        parsed = parse_qsl(data, keep_blank_values=True, encoding=enc)
        return {i[0]: i[1] for i in parsed}

    r = request_dict
    r["headers"] = HeadersDict(request_dict["headers"])
    content_type_encoding = get_encoding_from_headers(r["headers"])
    encoding = content_type_encoding or DEFAULT_ENCODING
    if isinstance(r["query_string"], six.binary_type):
        r["query_string"] = r["query_string"].decode(encoding)
    r["query_string"] = convert_params_to_dict(r["query_string"], encoding)
    if isinstance(r["body"], six.binary_type):
        r["body"] = r["body"].decode(encoding)
    content_type, options = parse_options_header(r["headers"].get("Content-Type"))
    charset = options.get("charset", DEFAULT_ENCODING)
    if content_type == "application/x-www-form-urlencoded":
        r["body"] = convert_params_to_dict(r["body"], charset)
    r["context"] = context
    if context is None:
        r["context"] = {}
