"""Optional drf-spectacular integration for endpoint lifecycle metadata.

Import this module only in projects that install drf-spectacular. The package's
core runtime deliberately has no dependency on the schema generator.
"""

try:
    from drf_spectacular.openapi import AutoSchema
except ImportError as exc:  # pragma: no cover - depends on optional integration
    raise ImportError(
        "EndpointLifecycleAutoSchema requires drf-spectacular. Install the "
        "optional schema tooling in your project before configuring "
        "REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS']."
    ) from exc

from .registry import registry


class EndpointLifecycleAutoSchema(AutoSchema):
    """Mark the exact registered DRF operation deprecated in generated schemas.

    drf-spectacular's NamespaceVersioning path resolves the version-adjusted
    URL and attaches its ResolverMatch to the schema view's request. The
    registry then identifies the operation using that resolver match and the
    concrete HTTP method/action. Missing or ambiguous identities fail closed.
    """

    def get_operation(self, path, path_regex, path_prefix, method, registry_schema):
        operation_schema = super().get_operation(
            path, path_regex, path_prefix, method, registry_schema
        )
        if operation_schema is None:
            return None

        request = getattr(self.view, "request", None)
        resolver_match = getattr(request, "resolver_match", None)
        if resolver_match is not None:
            resolved_operation = registry.resolve_operation(resolver_match, method)
        else:
            # drf-spectacular's URLPathVersioning branch injects the requested
            # version into view.kwargs but does not create a ResolverMatch.
            from rest_framework.versioning import URLPathVersioning

            versioning_class = getattr(self.view, "versioning_class", None)
            if (
                not isinstance(versioning_class, type)
                or not issubclass(versioning_class, URLPathVersioning)
            ):
                return operation_schema

            logical_endpoint_attr = registry._LOGICAL_ENDPOINT_ATTR
            logical_endpoint = getattr(self.view, logical_endpoint_attr, None)
            version_param = getattr(versioning_class, "version_param", "version")
            kwargs = getattr(self.view, "kwargs", {}) or {}
            version = kwargs.get(version_param)
            if isinstance(version, bool):
                return operation_schema
            if isinstance(version, str) and version.isdecimal():
                version = int(version)
            if not isinstance(version, int):
                return operation_schema

            resolved_operation = registry.resolve_registered_operation(
                logical_endpoint, version, method
            )

        if resolved_operation is None:
            return operation_schema

        lifecycle = registry.get_endpoint_lifecycle(resolved_operation)
        if lifecycle is not None and lifecycle.deprecated_at is not None:
            # Only add the standard OpenAPI flag. Never write False, because
            # explicit @extend_schema(deprecated=True) must remain authoritative.
            operation_schema["deprecated"] = True

        return operation_schema
