from .account_attributes import AccountAttributes
from .amazon_dev_pay import AmazonDevPay
from .amis import AmisResponse
from .availability_zones_and_regions import AvailabilityZonesAndRegions
from .customer_gateways import CustomerGateways
from .dhcp_options import DHCPOptions
from .elastic_block_store import ElasticBlockStore
from .elastic_ip_addresses import ElasticIPAddresses
from .elastic_network_interfaces import ElasticNetworkInterfaces
from .general import General
from .instances import InstanceResponse
from .internet_gateways import InternetGateways
from .egress_only_internet_gateways import EgressOnlyInternetGateway
from .ip_addresses import IPAddresses
from .key_pairs import KeyPairs
from .launch_templates import LaunchTemplates
from .monitoring import Monitoring
from .network_acls import NetworkACLs
from .placement_groups import PlacementGroups
from .reserved_instances import ReservedInstances
from .route_tables import RouteTables
from .security_groups import SecurityGroups
from .spot_fleets import SpotFleets
from .spot_instances import SpotInstances
from .subnets import Subnets
from .flow_logs import FlowLogs
from .tags import TagResponse
from .virtual_private_gateways import VirtualPrivateGateways
from .vm_export import VMExport
from .vm_import import VMImport
from .vpcs import VPCs
from .vpc_peering_connections import VPCPeeringConnections
from .vpn_connections import VPNConnections
from .windows import Windows
from .nat_gateways import NatGateways
from .transit_gateways import TransitGateways
from .transit_gateway_route_tables import TransitGatewayRouteTable
from .transit_gateway_attachments import TransitGatewayAttachment
from .iam_instance_profiles import IamInstanceProfiles
from .carrier_gateways import CarrierGateway


class EC2Response(
    AccountAttributes,
    AmazonDevPay,
    AmisResponse,
    AvailabilityZonesAndRegions,
    CustomerGateways,
    DHCPOptions,
    ElasticBlockStore,
    ElasticIPAddresses,
    ElasticNetworkInterfaces,
    General,
    InstanceResponse,
    InternetGateways,
    EgressOnlyInternetGateway,
    IPAddresses,
    KeyPairs,
    LaunchTemplates,
    Monitoring,
    NetworkACLs,
    PlacementGroups,
    ReservedInstances,
    RouteTables,
    SecurityGroups,
    SpotFleets,
    SpotInstances,
    Subnets,
    FlowLogs,
    TagResponse,
    VirtualPrivateGateways,
    VMExport,
    VMImport,
    VPCs,
    VPCPeeringConnections,
    VPNConnections,
    Windows,
    NatGateways,
    TransitGateways,
    TransitGatewayRouteTable,
    TransitGatewayAttachment,
    IamInstanceProfiles,
    CarrierGateway,
):
    @property
    def ec2_backend(self):
        from moto.ec2.models import ec2_backends

        return ec2_backends[self.region]

    @property
    def should_autoescape(self):
        return True

    def _dispatch(self, request, full_url, headers):
        from moto.motocore.loaders import _load_service_model
        from moto.motocore.serialize import create_serializer

        self.setup_class(request, full_url, headers)
        model = _load_service_model("ec2", api_version=self._get_param("Version"))
        self.operation_model = model.operation_model(self._get_action())
        self.serializer = create_serializer("query")
        self.serializer.ALIASES.update({"Ami": "Image"})
        return self.call_action()

    def response_template(self, source):
        supported_actions = [
            "CreateImage",
            "DescribeImages",
            "CopyImage",
            "RegisterImage",
            "DeregisterImage",
            "RunInstances",
            "DescribeInstances",
            "DescribeVolumes",
            "DescribeSnapshots",
            "TerminateInstances",
            "DescribeTags",
            #         'DescribeImageAttribute',
        ]
        source_action = source.strip().partition("Response")[0][1:]
        if source_action in supported_actions:
            return self
        return super(AmisResponse, self).response_template(source)

    def render(self, **kwargs):
        if self.operation_model.name in ["CreateImage", "CopyImage", "RegisterImage"]:
            kwargs = {"image_id": kwargs.get("image").id}
        elif self.operation_model.name in ["RunInstances"]:
            kwargs = kwargs.get("reservation", object)
        elif self.operation_model.name in ["DescribeImageAttribute"]:
            kwargs["image_id"] = kwargs["ami_id"]

        serialized = self.serializer.serialize_object(kwargs, self.operation_model)
        serialized = self.serializer.serialize_to_response(kwargs, self.operation_model)
        return serialized
