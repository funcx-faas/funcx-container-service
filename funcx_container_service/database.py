# not really a database, just dump everything in the fs for now

import json
import uuid
import asyncio
import hashlib
from datetime import datetime
from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import (create_engine, Column, String, Integer,
                        ForeignKey, DateTime, Enum)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool

from .models import ContainerState, StatusResponse
from . import build


RUN_ID = str(uuid.uuid4())

Base = declarative_base()
Session = sessionmaker()
_engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool)
Session.configure(bind=_engine)


class Container(Base):
    __tablename__ = 'containers'

    id = Column(String, primary_key=True)
    last_used = Column(DateTime)
    state = Column(Enum(ContainerState))
    specification = Column(String)
    docker_size = Column(Integer)
    singularity_size = Column(Integer)
    builder = Column(String)

    builds = relationship('Build', back_populates='container')


class Build(Base):
    __tablename__ = 'builds'

    id = Column(String, primary_key=True)
    container_hash = Column(String, ForeignKey('containers.id'))
    # Add auth/user info

    container = relationship('Container', back_populates='builds')


@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except:  # noqa: E722
        session.rollback()
        raise
    finally:
        session.close()


def hash_file(pth):
    digest = hashlib.sha256()
    with open(pth, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()


async def store_spec(db, spec):
    container_id = spec.digest()

    for row in db.query(Container).filter(Container.id == container_id):
        return container_id

    cont = Container()
    cont.id = container_id
    cont.last_used = datetime.now()
    cont.specification = spec.json()
    cont.state = ContainerState.pending
    db.add(cont)

    return container_id


async def store_tarball(db, s3, tarball):
    tarball.rollover()
    container_id = await asyncio.to_thread(hash_file, tarball.name)

    for row in db.query(Container).filter(Container.id == container_id):
        return container_id

    await asyncio.to_thread(
            s3.upload_file, tarball.name, 'repos', container_id)

    cont = Container()
    db.add(cont)
    cont.id = container_id
    cont.last_used = datetime.now()
    cont.state = ContainerState.pending

    return container_id


async def get_spec(db, build_id):
    for row in db.query(Build).filter(Build.id == build_id):
        build = row
        break
    else:
        raise HTTPException(status_code=404)

    spec = build.container.specification
    if not spec:
        raise HTTPException(status_code=400)

    return json.loads(spec)


async def add_build(db, container_id):
    build = Build()
    build.id = str(uuid.uuid4())
    build.container_hash = container_id
    db.add(build)
    db.commit()  # needed to get relationships
    build.container.last_used = datetime.now()
    return build.id


async def status(db, build_id):
    for row in db.query(Build).filter(Build.id == build_id):
        build = row
        container = row.container
        break
    else:
        raise HTTPException(status_code=404)

    return StatusResponse(
        id=build.id,
        recipe_checksum=container.id,
        last_used=container.last_used,
        docker_size=container.docker_size,
        singularity_size=container.singularity_size,
        status=container.state
        )


async def start_build(db, container_id):
    container = db.query(Container).filter(
            Container.id == container_id).populate_existing(
            ).with_for_update().one()
    try:
        if container.state == ContainerState.ready:
            # nothing to do
            return False
        elif container.state == ContainerState.failed:
            # already failed, not going to change
            return False
        elif (container.state == ContainerState.building
                and container.builder == RUN_ID):
            # build already started by this server
            return False
        elif container.state == ContainerState.building:
            # build from a previous (crashed) server, clean up
            await build.remove(db, container_id)

        container.state = ContainerState.building
        container.builder = RUN_ID
        return True
    finally:
        db.commit()


Base.metadata.create_all(_engine)
