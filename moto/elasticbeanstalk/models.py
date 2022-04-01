import weakref

from moto.core import BaseBackend, BaseModel, ACCOUNT_ID
from moto.core.utils import BackendDict
from .exceptions import InvalidParameterValueError, ResourceNotFoundException
from .utils import make_arn


class Environment(BaseModel):
    def __init__(
        self, application, environment_name, solution_stack_name, tags,
    ):
        self.application = weakref.proxy(
            application
        )  # weakref to break circular dependencies
        self.environment_name = environment_name
        self.solution_stack_name = solution_stack_name
        self.tags = tags

    @property
    def application_name(self):
        return self.application.application_name

    @property
    def environment_arn(self):
        resource_path = "%s/%s" % (self.application_name, self.environment_name)
        return make_arn(self.region, ACCOUNT_ID, "environment", resource_path)

    @property
    def platform_arn(self):
        return "TODO"  # TODO

    @property
    def region(self):
        return self.application.region


class Application(BaseModel):
    def __init__(self, backend, application_name):
        self.backend = weakref.proxy(backend)  # weakref to break cycles
        self.application_name = application_name
        self.environments = dict()

    def create_environment(
        self, environment_name, solution_stack_name, tags,
    ):
        if environment_name in self.environments:
            raise InvalidParameterValueError

        env = Environment(
            application=self,
            environment_name=environment_name,
            solution_stack_name=solution_stack_name,
            tags=tags,
        )
        self.environments[environment_name] = env

        return env

    @property
    def region(self):
        return self.backend.region

    @property
    def arn(self):
        return make_arn(self.region, ACCOUNT_ID, "application", self.application_name)


class EBBackend(BaseBackend):
    def __init__(self, region):
        self.region = region
        self.applications = dict()

    def reset(self):
        # preserve region
        region = self.region
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "elasticbeanstalk"
        ) + BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "elasticbeanstalk-health"
        )

    def create_application(self, application_name):
        if application_name in self.applications:
            raise InvalidParameterValueError(
                "Application {} already exists.".format(application_name)
            )
        new_app = Application(backend=self, application_name=application_name,)
        self.applications[application_name] = new_app
        return new_app

    def describe_applications(self):
        return self.applications.values()

    def create_environment(
        self, application_name, environment_name=None, stack_name=None, tags=None
    ):
        try:
            app = self.applications[application_name]
        except KeyError:
            raise InvalidParameterValueError(
                "No Application named '{}' found.".format(application_name)
            )

        return app.create_environment(
            environment_name=environment_name,
            solution_stack_name=stack_name,
            tags=tags,
        )

    def describe_environments(self):
        envs = []
        for app in self.applications.values():
            for env in app.environments.values():
                envs.append(env)
        return envs

    def list_available_solution_stacks(self):
        # Implemented in response.py
        pass

    def update_tags_for_resource(self, resource_arn, tags_to_add, tags_to_remove):
        try:
            res = self._find_environment_by_arn(resource_arn)
        except KeyError:
            raise ResourceNotFoundException(
                "Resource not found for ARN '{}'.".format(resource_arn)
            )

        for tag in tags_to_add:
            existing_tag = next((t for t in res.tags if t["key"] == tag["key"]), None)
            if existing_tag is None:
                res.tags.append(tag)
            else:
                existing_tag["value"] = tag["value"]

        for key in tags_to_remove:
            existing_tag = next((t for t in res.tags if t["key"] == key), None)
            if existing_tag is not None:
                res.tags.remove(existing_tag)

    def list_tags_for_resource(self, resource_arn):
        try:
            res = self._find_environment_by_arn(resource_arn)
        except KeyError:
            raise ResourceNotFoundException(
                "Resource not found for ARN '{}'.".format(resource_arn)
            )
        return {"ResourceArn": resource_arn, "ResourceTags": res.tags}

    def _find_environment_by_arn(self, arn):
        for app in self.applications.keys():
            for env in self.applications[app].environments.values():
                if env.environment_arn == arn:
                    return env
        raise KeyError()


eb_backends = BackendDict(EBBackend, "elasticbeanstalk")
