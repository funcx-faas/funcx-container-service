import uuid
from . import callback_router
from .models import ContainerSpec, BuildStatus


class Container():

    """
    A class used to house the information and functionality  needed to build a
    docker image that provides an environment in which a ML model can be
    deployed on the funcX service for inference.
    """

    def __init__(self, container_spec: ContainerSpec, RUN_ID):
        self.container_spec = container_spec
        self.container_id = container_spec.container_id
        self.build_id = str(uuid.uuid4())
        self.RUN_ID = RUN_ID
        self.build_status = BuildStatus.queued
        self.container_build_process = None
        self.build_spec = None

    """
    from definition of container object in database.py:
    id = Column(String, primary_key=True)
    last_used = Column(DateTime)
    state = Column(Enum(BuildStatus))
    specification = Column(String)
    docker_size = Column(Integer)
    singularity_size = Column(Integer)
    builder = Column(String)
    """

    async def register(self, settings):
        self.container_id = await callback_router.register_container_spec(self.container_spec, settings)

    async def register_building(self, RUN_ID, settings):
        build_result = await callback_router.register_building(self,
                                                               settings)
        return build_result

    async def register_build_complete(self, completion_spec, settings):

        # post_dict = {**self.container_spec, **BuildCompletionSpec}

        build_complete_result = await callback_router.register_build_complete(completion_spec, settings)

        return build_complete_result

    def start_build(self, RUN_ID, settings):

        if self.build_status == BuildStatus.ready:
            # nothing to do
            return False
        elif self.build_status == BuildStatus.failed:
            # already failed, not going to change
            return False
        elif (self.build_status == BuildStatus.building and self.container_build_process == RUN_ID):
            # build already started by this server
            return False
        elif self.build_status == BuildStatus.building:
            # build from a previous (crashed) server, clean up
            # await build.remove(db, container_id)

            # TODO: removed due to circular import, but what does this do?
            # build.remove(self.container_id)
            pass

        self.build_status = BuildStatus.building
        self.container_build_process = RUN_ID
        return True
