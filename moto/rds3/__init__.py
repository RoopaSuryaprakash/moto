from .models import rds3_backends
from ..core.models import base_decorator

rds3_backend = rds3_backends["us-west-1"]
mock_rds3 = base_decorator(rds3_backends)
