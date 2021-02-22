from sqlalchemy import and_, func
from . import database, build
from .models import ContainerSpec, ContainerState


MAX_STORAGE = None
ALPHA = 0.5


def jaccard(a, b):
    return 1 - float(len(a & b))/len(a | b)


def spec_to_set(spec):
    out = set()
    if spec.apt:
        out.update({f'a{x}' for x in spec.apt})
    if spec.conda:
        out.update({f'c{x}' for x in spec.conda})
    if spec.pip:
        out.update({f'p{x}' for x in spec.pip})
    return out


def total_storage():
    with database.session_scope() as session:
        size = session.query(database.Container).with_entities(
                func.sum(database.Container.docker_size
                         + database.Container.singularity_size)).scalar()
        return size or 0


async def cleanup(db):
    if MAX_STORAGE is None:
        return
    while total_storage() > MAX_STORAGE:
        container = db.query(database.Container).filter(
                database.Container.docker_size.isnot(None)
                ).order_by(database.Container.last_used.asc()).first()
        await build.remove(db, container.id)
        db.commit()


async def find_existing(db, spec):
    if spec is None:
        return

    target = spec_to_set(spec)
    best = None
    best_distance = 2.0  # greater than any jaccard distance, effectively inf.

    for container in db.query(database.Container).filter(and_(
            database.Container.state == ContainerState.ready,
            database.Container.specification.isnot(None))):
        other = spec_to_set(ContainerSpec.parse_raw(container.specification))
        if not target.issubset(other):
            continue
        distance = jaccard(target, other)
        if distance > ALPHA:
            continue
        if distance < best_distance:
            best_distance = distance
            best = container

    return best
