from botocore.session import get_session
from moto.motocore.regions import EndpointResolver

# TODO: Test with fake endpoint data so we can ensure tests don't break...


def test_endpoint_deconstruction():
    session = get_session()
    loader = session.get_component("data_loader")
    endpoint_data = loader.load_data("endpoints")
    deconstructor = EndpointResolver(endpoint_data)
    result = deconstructor.deconstruct_endpoint("rds.us-west-2.amazonaws.com")
    assert result["region"] == "us-west-2"
    assert result["partition"] == "aws"
    assert result["service"] == "rds"
    # This tests {region}.{service} as well as service alias
    result = deconstructor.deconstruct_endpoint(
        "us-west-1.elasticmapreduce.amazonaws.com"
    )
    assert result["region"] == "us-west-1"
    assert result["partition"] == "aws"
    assert result["service"] == "elasticmapreduce"


def test_endpoint_without_region():
    session = get_session()
    loader = session.get_component("data_loader")
    endpoint_data = loader.load_data("endpoints")
    deconstructor = EndpointResolver(endpoint_data)
    result = deconstructor.deconstruct_endpoint("iam.amazonaws.com")
    assert result["partition"] == "aws"
    assert result["service"] == "iam"
    assert result["region"] == "aws-global"
