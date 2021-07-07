# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Builtin event handlers.

This module contains builtin handlers for events emitted by motocore.

List out all the possible events and arguments
 -
"""

import logging
import random
from botocore import xform_name


logger = logging.getLogger(__name__)


# This was a sample one from botocore
def inject_api_version_header_if_needed(model, params, **kwargs):
    if not model.is_endpoint_discovery_operation:
        return
    params["headers"]["x-amz-api-version"] = model.service_model.api_version


def fix_ec2_request_issues(parsed_request, operation_model, context, **kwargs):
    if operation_model.name == "RunInstances":
        parsed_request["action"] = "add_instances"
        params = parsed_request["kwargs"]
        params["count"] = params.get("min_count", 1)
        params["security_group_names"] = params.get("security_group", [])
        params["user_data"] = params.get("user_data", None)
    elif operation_model.name == "CreateSubnet":
        params = parsed_request["kwargs"]
        if "availability_zone" not in params:
            from moto.ec2 import ec2_backends

            backend = ec2_backends[context["region"]]
            params["availability_zone"] = random.choice(
                backend.describe_availability_zones()
            ).name


def fix_ec2_result_issues(result_dict, operation_model, **kwargs):
    # Basically we have to make attrs name in their Python equivalent
    if operation_model.name == "RunInstances":
        value = result_dict["result"]
        value.reservation_id = value.id
        value.instances_set = value.instances
        for instance in value.instances_set:
            instance.instance_id = instance.id
    elif operation_model.name == "DescribeAvailabilityZones":
        value = result_dict["result"]
        for item in value:
            item.zone_name = item.name
    elif operation_model.name == "CreateVpc":
        value = result_dict["result"]
        value.vpc_id = value.id
    elif operation_model.name == "CreateSubnet":
        value = result_dict["result"]
        value.subnet_id = value.id


def fix_elasticbeanstalk_result_issues(result_dict, operation_model, **kwargs):
    if operation_model.name == "CreateEnvironment":
        return result_dict.pop("result")


def fix_emr_request_issues(parsed_request, operation_model, **kwargs):
    if operation_model.name == "RunJobFlow":
        params = parsed_request["kwargs"]
        params["instance_attrs"] = params.pop("instances")
        params["steps"] = params.get("steps", [])
        bootstrap_actions = params.pop("bootstrap_actions", [])
        params["bootstrap_actions"] = []
        for action in bootstrap_actions:
            ba = {
                "name": action["name"],
                "script_path": action["script_bootstrap_action"].get("path", ""),
                "args": action["script_bootstrap_action"].get("args", []),
            }
            params["bootstrap_actions"].append(ba)


def fix_emr_result_issues(result_dict, operation_model, **kwargs):
    pass


def fix_kms_request_issues(parsed_request, operation_model, **kwargs):
    if operation_model.name == "CreateKey":
        params = parsed_request["kwargs"]
        default_to_none = [
            "customer_master_key_spec",
            "tags",
            "region",
            "policy",
            "key_usage",
        ]
        for param in default_to_none:
            if param not in params:
                params[param] = None


def fix_kms_result_issues(result_dict, operation_model, **kwargs):
    # Basically we have to make attrs name in their Python equivalent
    if operation_model.name == "CreateKey":
        value = result_dict["result"]
        value.key_id = value.id


def fix_polly_request_issues(parsed_request, operation_model, **kwargs):
    if operation_model.name == "DescribeVoices":
        params = parsed_request["kwargs"]
        if "language_code" not in params:
            params["language_code"] = None
        if "next_token" not in params:
            params["next_token"] = None


def fix_polly_result_issues(result_dict, operation_model, **kwargs):
    if operation_model.name == "DescribeVoices":
        value = result_dict["result"]
        new_value = []
        for item in value:
            new_item = {}
            for key in item.keys():
                new_item[xform_name(key)] = item[key]
            new_value.append(new_item)
        result_dict["result"] = new_value


def fix_redshift_request_issues(parsed_request, operation_model, context, **kwargs):
    params = parsed_request["kwargs"]
    if operation_model.name in [
        "CreateCluster",
        "CreateClusterSubnetGroup",
        "CreateClusterSecurityGroup",
        "CreateClusterParameterGroup",
    ]:
        # This is because the current responses passes this in instead of
        # letting the backend figure it out...
        params["region_name"] = context["region"]
    if operation_model.name == "CreateCluster":
        if "iam_roles" in params:
            params["iam_roles_arn"] = params.pop("iam_roles")
    if operation_model.name == "CreateClusterParameterGroup":
        if "parameter_group_name" in params:
            params["cluster_parameter_group_name"] = params.pop("parameter_group_name")
        if "parameter_group_family" in params:
            params["group_family"] = params.pop("parameter_group_family")
    if operation_model.name == "DeleteCluster":
        params["skip_final_snapshot"] = params.pop("skip_final_cluster_snapshot", False)
    if operation_model.name == "DescribeClusterSubnetGroups":
        params["subnet_identifier"] = params.pop("cluster_subnet_group_name", None)
    if operation_model.name == "CreateTags":
        # Have to make this case insensitive because the current
        # redshift response method calls the backend with Pascal Case.
        from botocore.awsrequest import HeadersDict as CaseInsensitiveDict

        params["tags"] = [CaseInsensitiveDict(**tag) for tag in params["tags"]]


def fix_redshift_result_issues(result_dict, operation_model, **kwargs):
    pass


def fix_sqs_request_issues(parsed_request, operation_model, context, **kwargs):
    if operation_model.name == "CreateQueue":
        params = parsed_request["kwargs"]
        params["name"] = params.pop("queue_name")


def fix_sqs_result_issues(result_dict, operation_model, **kwargs):
    if operation_model.name == "CreateQueue":
        pass


def fix_ssm_request_issues(parsed_request, operation_model, context, **kwargs):
    if operation_model.name == "AddTagsToResource":
        params = parsed_request["kwargs"]
        params["tags"] = {t["key"]: t["value"] for t in params["tags"]}
    elif operation_model.name == "RemoveTagsFromResource":
        params = parsed_request["kwargs"]
        params["keys"] = params.pop("tag_keys")


def fix_ssm_result_issues(result_dict, operation_model, **kwargs):
    if operation_model.name == "ListTagsForResource":
        value = result_dict["result"]
        tag_list = [{"key": k, "value": v} for (k, v) in value.items()]
        result_dict["result"] = {"tag_list": tag_list}


# This is a list of (event_name, handler).
# When our custom client is created, everything in this list will be
# automatically registered with that Session.
CUSTOM_HANDLERS = [
    # EC2
    ("request-after-parsing.ec2.*", fix_ec2_request_issues),
    # We can do these with ec2.*  I was just doing them fully qualified to test them...
    # ("before-result-serialization.ec2.DescribeAvailabilityZones", fix_ec2_result_issues),
    # ("before-result-serialization.ec2.RunInstances", fix_ec2_result_issues),
    ("before-result-serialization.ec2.*", fix_ec2_result_issues),
    # ElasticBeanStalk
    (
        "before-result-serialization.elastic-beanstalk.*",
        fix_elasticbeanstalk_result_issues,
    ),
    # EMR
    ("request-after-parsing.emr.*", fix_emr_request_issues),
    ("before-result-serialization.emr.*", fix_emr_result_issues),
    # KMS
    ("request-after-parsing.kms.*", fix_kms_request_issues),
    ("before-result-serialization.kms.*", fix_kms_result_issues),
    # Polly
    ("request-after-parsing.polly.*", fix_polly_request_issues),
    ("before-result-serialization.polly.*", fix_polly_result_issues),
    # Redshift
    ("request-after-parsing.redshift.*", fix_redshift_request_issues),
    ("before-result-serialization.redshift.*", fix_redshift_result_issues),
    # SQS
    ("request-after-parsing.sqs.*", fix_sqs_request_issues),
    ("before-result-serialization.sqs.*", fix_sqs_result_issues),
    # SSM
    ("request-after-parsing.ssm.*", fix_ssm_request_issues),
    ("before-result-serialization.ssm.*", fix_ssm_result_issues),
]
