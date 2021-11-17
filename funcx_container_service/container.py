import uuid
from . import callback_router
from .models import BuildSpec, ContainerSpec, ContainerState


class Container():
    """
    A class used to house the information and functionality  needed to build a
    docker image that provides an environment in which a ML model can be 
    deployed on the funcX service for inference.
    """
    
    def __init__(self, container_spec: ContainerSpec):
        self.container_spec = container_spec
        self.container_id = container_spec.container_id
        self.build_status = None
        self.container_state = None
        self.container_build_process = None
        self.build_spec = None
        self.container_state = ContainerState.pending

    """
    from definition of container object in database.py:
    id = Column(String, primary_key=True)
    last_used = Column(DateTime)
    state = Column(Enum(ContainerState))
    specification = Column(String)
    docker_size = Column(Integer)
    singularity_size = Column(Integer)
    builder = Column(String)
    """

    async def register(self, settings):
        self.container_id = await callback_router.register_container_spec(self.container_spec, settings)

    async def register_build(self, RUN_ID, settings):
        build_id = str(uuid.uuid4())
        build_spec = BuildSpec(container_id=self.container_id,
                               build_id=build_id,
                               RUN_ID=RUN_ID)

        self.build_spec = build_spec

        build_result = await callback_router.register_build(build_spec,
                                                            settings)
        return build_result

    def start_build(self, RUN_ID, settings):
        try:
            if self.container_state == ContainerState.ready:
                # nothing to do
                return False
            elif self.container_state == ContainerState.failed:
                # already failed, not going to change
                return False
            elif (self.container_state == ContainerState.building
                    and self.container_build_process == RUN_ID):
                # build already started by this server
                return False
            elif self.container_state == ContainerState.building:
                # build from a previous (crashed) server, clean up
                # await build.remove(db, container_id)

                # TODO: removed due to circular import, but what does this do?
                # build.remove(self.container_id)
                pass

            self.container_state = ContainerState.building
            self.container_build_process = RUN_ID
            return True

        finally:
            callback_router.update_container(self, settings)
