# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Resolves regions and endpoints.

This module implements endpoint resolution, including resolving endpoints for a
given service and region and resolving the available endpoints for a service
in a specific AWS partition.
"""
import logging

from botocore.regions import EndpointResolver as BotocoreEndpointResolver

LOG = logging.getLogger(__name__)


class EndpointResolver(BotocoreEndpointResolver):

    SERVICES_BLACKLIST = [
        'docdb',    # This conflicts with RDS.
        'neptune',  # This also conflicts with RDS...
    ]

    def deconstruct_endpoint(self, hostname):
        # Iterate over each partition until a match is found.
        results = []
        for partition in self._endpoint_data['partitions']:
            for service in partition['services']:
                if service in EndpointResolver.SERVICES_BLACKLIST:
                    continue
                for region in partition['services'][service]['endpoints']:
                    ep = self._endpoint_for_partition(partition, service, region)
                    if hostname in [
                        ep.get('sslCommonName'),
                        ep.get('hostname'),
                    ]:
                        result = {'service': service, 'partition': partition['partition'], 'region': region}
                        results.append(result)
        # Bleh... this can result in a number of matches docdb and rds, for example
        return results[0]
