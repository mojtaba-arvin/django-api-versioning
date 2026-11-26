"""Pure projections of immutable route snapshots into compatibility matrices."""

from typing import Callable

from ..route_state import RegistrySnapshot

VersionMatrix = dict[str, dict[int | None, Callable]]

REMOVED_ROUTE = object()
_ROUTER_OWNER_IDENTITY = object()


def project_version_matrix(snapshot: RegistrySnapshot) -> VersionMatrix:
    """Project physical route/version callbacks and explicit tombstones."""
    matrix: VersionMatrix = {}
    for record in snapshot.active_routes:
        matrix.setdefault(record.route, {})[
            record.route_version
        ] = record.implementation
    for record in snapshot.removed_routes:
        matrix.setdefault(record.route, {}).setdefault(
            record.route_version, REMOVED_ROUTE
        )
    return matrix


def _owner_identity(record) -> tuple[object, ...] | None:
    """Return the stable grouping identity for an owned or unowned route."""
    if record.owner == "unowned":
        return None
    return (
        _ROUTER_OWNER_IDENTITY,
        record.router_prefix,
        record.trailing_slash,
    )


def project_logical_version_matrix(snapshot: RegistrySnapshot) -> VersionMatrix:
    """Project logical endpoint/version callbacks without losing route collisions."""
    entries = []

    def add_entry(record, callback):
        logical_id = (
            record.logical_endpoint
            if record.logical_endpoint is not None
            else record.route
        )
        entries.append(
            (
                logical_id,
                record.route_version,
                record,
                callback,
                _owner_identity(record),
            )
        )

    for record in snapshot.active_routes:
        add_entry(record, record.implementation)
    for record in snapshot.removed_routes:
        add_entry(record, REMOVED_ROUTE)

    counts = {}
    owner_groups = {}
    for logical_id, route_version, _record, _callback, owner_identity in entries:
        identity = (logical_id, route_version)
        counts[identity] = counts.get(identity, 0) + 1
        owner_groups.setdefault(logical_id, set()).add(owner_identity)

    matrix: VersionMatrix = {}
    for logical_id, route_version, record, callback, owner_identity in entries:
        has_multiple_owners = len(owner_groups[logical_id]) > 1
        has_same_version_collision = counts[(logical_id, route_version)] > 1

        if has_multiple_owners or has_same_version_collision:
            if owner_identity is None:
                discriminator = f"route={record.route!r}"
            else:
                discriminator = (
                    f"router={record.router_prefix!r}, "
                    f"trailing_slash={record.trailing_slash!r}"
                )
            matrix_key = f"{logical_id} [{discriminator}]"
        else:
            matrix_key = logical_id

        matrix.setdefault(matrix_key, {})[route_version] = callback

    return matrix
