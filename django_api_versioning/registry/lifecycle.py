"""Endpoint-scoped lifecycle metadata storage and composition rules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..exceptions import (
    InvalidVersionError,
    VersioningError,
    VersionRangeError,
    VersionTypeError,
)
from ..lifecycle_metadata import EndpointLifecycle, parse_endpoint_lifecycle
from ..settings import api_settings

if TYPE_CHECKING:
    from .resolution import ResolvedOperation


class EndpointLifecycleStore:
    """Own lifecycle declarations for one UrlRegistry instance."""

    def __init__(self) -> None:
        self.records: dict[
            tuple[str, int, str | None, str | None, object | None],
            EndpointLifecycle,
        ] = {}

    def snapshot(
        self,
    ) -> dict[
        tuple[str, int, str | None, str | None, object | None], EndpointLifecycle
    ]:
        """Capture an isolated transaction snapshot."""
        return dict(self.records)

    def restore(
        self,
        state: dict[
            tuple[str, int, str | None, str | None, object | None],
            EndpointLifecycle,
        ],
    ) -> None:
        """Restore in place so compatibility views retain object identity."""
        self.records.clear()
        self.records.update(state)

    def clear(self) -> None:
        self.records.clear()

    def register(
        self,
        logical_endpoint: str,
        route_version: int,
        *,
        method: str | None = None,
        action: str | None = None,
        deprecated_at: str | None = None,
        sunset: str | None = None,
        owner: object | None = None,
    ) -> None:
        """Validate and register one idempotent lifecycle declaration."""
        if not isinstance(logical_endpoint, str) or not logical_endpoint:
            raise VersioningError("logical_endpoint must be a non-empty string.")
        if isinstance(route_version, bool) or not isinstance(route_version, int):
            raise VersionTypeError("Endpoint lifecycle version must be an integer.")
        if route_version < api_settings.API_MIN_VERSION:
            raise VersionRangeError(
                f"Endpoint lifecycle version {route_version} is below "
                f"API_MIN_VERSION {api_settings.API_MIN_VERSION}."
            )
        if route_version > api_settings.API_MAX_VERSION:
            raise InvalidVersionError(
                f"Endpoint lifecycle version {route_version} is above "
                f"API_MAX_VERSION {api_settings.API_MAX_VERSION}."
            )

        normalized_method = None
        if method is not None:
            if not isinstance(method, str) or not method.strip():
                raise VersioningError("Endpoint lifecycle method must be a string.")
            normalized_method = method.strip().upper()

        normalized_action = None
        if action is not None:
            if not isinstance(action, str) or not action.strip():
                raise VersioningError("Endpoint lifecycle action must be a string.")
            normalized_action = action.strip()

        lifecycle = parse_endpoint_lifecycle(deprecated_at, sunset)
        key = (
            logical_endpoint,
            route_version,
            normalized_method,
            normalized_action,
            owner,
        )
        existing = self.records.get(key)
        if existing is not None and existing != lifecycle:
            raise VersioningError(
                "Conflicting endpoint lifecycle declarations for "
                f"{logical_endpoint!r} version {route_version}."
            )
        self.records[key] = lifecycle

    def invalidate_for_removal(
        self,
        logical_endpoint: str,
        from_version: int,
        *,
        owner: object | None,
        preserved_versions: set[int],
    ) -> None:
        """Drop declarations belonging to removed route segments."""
        stale_keys = [
            key
            for key in self.records
            if key[4] is owner
            and key[0] == logical_endpoint
            and key[1] >= from_version
            and key[1] not in preserved_versions
        ]
        for key in stale_keys:
            del self.records[key]

    def get(self, operation: ResolvedOperation) -> EndpointLifecycle | None:
        """Compose applicable scopes monotonically, choosing earliest dates."""
        methods = (
            (operation.method, "GET")
            if operation.method == "HEAD"
            else (operation.method,)
        )
        scopes = [(None, None), (None, operation.action)]
        for method in methods:
            scopes.extend(((method, None), (method, operation.action)))

        records = []
        for method, action in dict.fromkeys(scopes):
            record = self.records.get(
                (
                    operation.logical_endpoint,
                    operation.route_version,
                    method,
                    action,
                    operation.router_owner,
                )
            )
            if record is not None:
                records.append(record)

        if not records:
            return None

        deprecation_dates = [
            record.deprecated_at
            for record in records
            if record.deprecated_at is not None
        ]
        sunset_dates = [
            record.sunset for record in records if record.sunset is not None
        ]
        return EndpointLifecycle(
            deprecated_at=min(deprecation_dates) if deprecation_dates else None,
            sunset=min(sunset_dates) if sunset_dates else None,
        )
