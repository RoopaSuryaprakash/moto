from moto.core import BackendDict, BaseBackend
from moto.ec2 import ec2_backends
from moto.iam import iam_backends
from moto.kms import kms_backends
from .db_cluster import DBCluster  # noqa: F401
from .db_cluster import DBClusterBackend
from .db_cluster_parameter_group import DBClusterParameterGroup  # noqa: F401
from .db_cluster_parameter_group import DBClusterParameterGroupBackend
from .db_cluster_snapshot import DBClusterSnapshot  # noqa: F401
from .db_cluster_snapshot import DBClusterSnapshotBackend
from .db_instance import DBInstance  # noqa: F401
from .db_instance import DBInstanceBackend
from .db_parameter_group import DBParameterGroup  # noqa: F401
from .db_parameter_group import DBParameterGroupBackend
from .db_security_group import DBSecurityGroup  # noqa: F401
from .db_security_group import DBSecurityGroupBackend
from .db_snapshot import DBSnapshot  # noqa: F401
from .db_snapshot import DBSnapshotBackend
from .db_subnet_group import DBSubnetGroup  # noqa: F401
from .db_subnet_group import DBSubnetGroupBackend
from .event import Event  # noqa: F401
from .event import EventBackend
from .log import DBLogFile  # noqa: F401
from .log import LogBackend
from .option_group import OptionGroup  # noqa: F401
from .option_group import OptionGroupBackend
from .tag import TagBackend


class RDS3Backend(
    BaseBackend,
    DBClusterBackend,
    DBClusterParameterGroupBackend,
    DBClusterSnapshotBackend,
    DBInstanceBackend,
    DBParameterGroupBackend,
    DBSecurityGroupBackend,
    DBSnapshotBackend,
    DBSubnetGroupBackend,
    EventBackend,
    LogBackend,
    OptionGroupBackend,
    TagBackend,
):
    def __init__(self, region_name, account_id):
        BaseBackend.__init__(self, region_name, account_id)
        for backend in RDS3Backend.__mro__:
            if backend not in [RDS3Backend, BaseBackend, object]:
                backend.__init__(self)
        # Create RDS Alias
        rds_key = self.kms.create_key(
            policy="",
            key_usage="ENCRYPT_DECRYPT",
            key_spec=None,
            description="Default master key that protects my RDS database volumes when no other key is defined",
            tags=None,
        )
        self.kms.add_alias(rds_key.id, "alias/aws/rds")

    @property
    def ec2(self):
        """
        :return: EC2 Backend
        :rtype: moto.ec2.models.EC2Backend
        """
        return ec2_backends[self.account_id][self.region_name]

    @property
    def iam(self):
        """
        :return: IAM Backend
        :rtype: moto.iam.models.IAMBackend
        """
        return iam_backends[self.account_id]["global"]

    @property
    def kms(self):
        """
        :return: KMS Backend
        :rtype: moto.kms.models.KMSBackend
        """
        return kms_backends[self.account_id][self.region_name]

    def get_regional_backend(self, region):
        """
        :return: RDS Backend
        :rtype: moto.rds3.models.RDS3Backend
        """
        return rds3_backends[self.account_id][region]


rds3_backends = BackendDict(RDS3Backend, "rds")
