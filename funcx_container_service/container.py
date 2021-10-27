import pdb

from . import build, callback_router
from .models import ContainerSpec, ContainerState


class Container():
    def __init__(self, container_spec: ContainerSpec):
        self.container_spec = container_spec
        self.container_id = None
        self.build_status = None
        self.container_state = None
        self.container_build_process = None

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

    def start_build(self, settings):
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
                build.remove(self.container_id)

            self.container_state = ContainerState.building
            self.container_build_process = RUN_ID
            return True

        finally:
            callback_router.update_container(self, settings)
