"""
Scenario catalogue for the Segment Lab.

A scenario = one views module + settings overrides + the requests and
reverse() calls to record. ``generate_routes.py`` runs every scenario in a
fresh Python process (the package keeps a process-global registry and reads
its settings once at import), so scenarios cannot leak into each other.

Select a scenario manually with:  LAB_SCENARIO=<name> python manage.py ...
"""
import os

LIFECYCLE = {
    1: {"status": "retired"},
    2: {"status": "deprecated", "sunset": "2099-06-01"},
    3: {"status": "active", "sunset": "2020-01-01"},
}

DRF_BASE = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

SCENARIOS: dict[str, dict] = {
    "main": {
        "title": "Contract change at v3",
        "question": "What does the registry contain after /users/ gets a new v3 view?",
        "views": "segment_lab.scenarios.main",
        "settings": {},
        "requests": [
            "/api/v1/users/",
            "/api/v2/users/",
            "/api/v3/users/",
            "/api/v3/users/7/",
            "/health/",
            "/api/v4/users/",
        ],
        "reverse": [
            ["api_reverse", "user-list", {"version": 1}],
            ["api_reverse", "user-list", {"version": 2}],
            ["api_reverse", "user-list", {"version": 3}],
            ["api_reverse", "user-detail", {"version": 3, "pk": 7}],
            ["api_reverse", "user-list", {}],
            ["api_reverse", "health", {}],
            ["django_reverse", "user-list", {}],
        ],
        "trace": True,
        "check_versions_variants": [["--skip-checks"]],
    },
    "existing_integration_project": {
        "title": "Existing integration project and DRF router",
        "question": "What does the repository's real Django integration project register, including routes owned by a separate DRF router?",
        "views": "api.views",
        "settings": {
            "API_MAX_VERSION": 4,
            "ROOT_URLCONF": "project.urls",
            "MIDDLEWARE": ["django_api_versioning.lifecycle.LifecycleMiddleware"],
        },
        "requests": [
            "/api/v1/users/",
            "/api/v2/users/",
            "/api/v3/users/",
            "/api/v4/users/",
            "/api/v1/blogposts/",
            "/api/v2/blogposts/",
            "/health/",
            "/api/v5/users/",
        ],
        "reverse": [
            ["api_reverse", "user-list-v1", {"version": 1}],
            ["api_reverse", "user-list-v2", {"version": 2}],
            ["api_reverse", "user-list-v3", {"version": 3}],
        ],
    },
    "before": {
        "title": "Before the contract change",
        "question": "What does the registry contain while every version still uses the v1 view?",
        "views": "segment_lab.scenarios.before",
        "settings": {"API_MAX_VERSION": 2},
        "requests": ["/api/v1/users/", "/api/v2/users/", "/api/v3/users/"],
        "reverse": [],
    },
    "max_bump": {
        "title": "API_MAX_VERSION raised, no code changed",
        "question": "What happens to existing declarations when API_MAX_VERSION goes from 3 to 4?",
        "views": "segment_lab.scenarios.main",
        "settings": {"API_MAX_VERSION": 4},
        "requests": ["/api/v4/users/", "/api/v4/users/7/"],
        "reverse": [],
    },
    "order_reversed": {
        "title": "Declaration order reversed",
        "question": "Does it matter whether the v3 declaration is imported before the v1 one?",
        "views": "segment_lab.scenarios.order_reversed",
        "settings": {},
        "requests": ["/api/v2/users/", "/api/v3/users/"],
        "reverse": [],
        "compare_matrix_with": "main",
    },
    "same_version": {
        "title": "Two views, same route, same version",
        "question": "Which view wins when two declarations start at the same version?",
        "views": "segment_lab.scenarios.same_version",
        "settings": {},
        "requests": ["/api/v1/users/", "/api/v3/users/"],
        "reverse": [],
    },
    "explicit_versions": {
        "title": "Explicit versions and ver_range",
        "question": "How do versions=[...] and ver_range() differ from version=N?",
        "views": "segment_lab.scenarios.explicit_versions",
        "settings": {"API_MAX_VERSION": 4},
        "requests": [
            "/api/v2/export/",
            "/api/v3/export/",
            "/api/v3/legacy/",
            "/api/v3/search/",
            "/api/v4/search/",
            "/api/v4/feed/",
        ],
        "reverse": [
            ["api_reverse", "export", {}],
            ["api_reverse", "search", {"version": 4}],
        ],
    },
    "min_version": {
        "title": "API_MIN_VERSION raised above a declaration",
        "question": "What happens to version=1 declarations when API_MIN_VERSION becomes 2?",
        "views": "segment_lab.scenarios.min_version",
        "settings": {"API_MIN_VERSION": 2, "API_MAX_VERSION": 3},
        "requests": ["/api/v2/users/", "/api/v3/users/", "/api/v2/orders/"],
        "reverse": [],
    },
    "route_identity": {
        "title": "Route identity is the literal string",
        "question": "Are 'users/' and 'users', or <int:pk> and <int:id>, the same route?",
        "views": "segment_lab.scenarios.route_identity",
        "settings": {},
        "requests": [
            "/api/v2/users/",
            "/api/v2/users",
            "/api/v2/users/7/",
        ],
        "reverse": [],
    },
    "no_import": {
        "title": "Views module never imported",
        "question": "What if nothing imports the module that contains the @endpoint declarations?",
        "views": None,
        "settings": {"LAB_VIEWS_MODULE": None},
        "requests": ["/api/v1/users/"],
        "reverse": [["api_reverse", "user-list", {"version": 1}]],
    },
    "drf_default": {
        "title": "DRF views, no versioning class",
        "question": "What is request.version in a DRF view registered with @endpoint?",
        "views": "segment_lab.scenarios.drf_views",
        "settings": {"REST_FRAMEWORK": dict(DRF_BASE)},
        "requests": [
            "/api/v2/invoices/",
            "/api/3/invoices/",
            "/api/v3/invoices/",
            "/api/v1/ping/",
            "/api/v2/receipts/",
            "/api/v2/receipts/summary/",
        ],
        "reverse": [],
    },
    "drf_urlpath": {
        "title": "DRF URLPathVersioning",
        "question": "Does URLPathVersioning read the version from package routes?",
        "views": "segment_lab.scenarios.drf_views",
        "settings": {
            "REST_FRAMEWORK": {
                **DRF_BASE,
                "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
            }
        },
        "requests": ["/api/v2/invoices/", "/api/v3/invoices/", "/api/v1/ping/"],
        "reverse": [],
    },
    "drf_urlpath_allowed": {
        "title": "DRF URLPathVersioning with ALLOWED_VERSIONS",
        "question": "What if URLPathVersioning also restricts ALLOWED_VERSIONS?",
        "views": "segment_lab.scenarios.drf_views",
        "settings": {
            "REST_FRAMEWORK": {
                **DRF_BASE,
                "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
                "ALLOWED_VERSIONS": ["1", "2", "3"],
            }
        },
        "requests": ["/api/v2/invoices/", "/api/v1/ping/"],
        "reverse": [],
    },
    "drf_urlpath_default": {
        "title": "URLPathVersioning with ALLOWED_VERSIONS and DEFAULT_VERSION",
        "question": "Does DEFAULT_VERSION make URLPathVersioning report the route's version?",
        "views": "segment_lab.scenarios.drf_views",
        "settings": {
            "REST_FRAMEWORK": {
                **DRF_BASE,
                "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
                "ALLOWED_VERSIONS": ["1", "2", "3"],
                "DEFAULT_VERSION": "1",
            }
        },
        "requests": ["/api/v3/invoices/"],
        "reverse": [],
    },
    "drf_viewset_class": {
        "title": "@endpoint on a ViewSet class",
        "question": "Can @endpoint decorate a DRF ViewSet class directly?",
        "views": "segment_lab.scenarios.drf_viewset_class",
        "settings": {},
        "requests": [],
        "reverse": [],
    },
    "drf_router": {
        "title": "DRF router next to @endpoint routes",
        "question": "Do router routes join the registry, and who serves a colliding path?",
        "views": "segment_lab.scenarios.drf_router",
        "settings": {},
        "requests": [
            "/api/v1/users/",
            "/api/v2/users/",
            "/api/v2/users/7/",
            "/api/v3/users/",
        ],
        "reverse": [],
    },
    "lifecycle": {
        "title": "LifecycleMiddleware",
        "question": "Which responses get Deprecation/Sunset headers or 410 Gone?",
        "views": "segment_lab.scenarios.lifecycle",
        "settings": {
            "MIDDLEWARE": ["django_api_versioning.lifecycle.LifecycleMiddleware"],
            "API_VERSION_LIFECYCLE": LIFECYCLE,
        },
        "requests": [
            "/api/v1/users/",
            "/api/v2/users/",
            "/api/v2/not-registered/",
            "/api/v3/users/",
            "/api/v3/not-registered/",
        ],
        "reverse": [],
        "trace": True,
    },
    "invalid": {
        "title": "Rejected declarations",
        "question": "Which declarations fail, and when?",
        "views": "segment_lab.scenarios.invalid",
        "settings": {},
        "requests": [],
        "reverse": [],
    },
}


def active_scenario_name() -> str:
    name = os.environ.get("LAB_SCENARIO", "main")
    if name not in SCENARIOS:
        raise SystemExit(
            f"Unknown LAB_SCENARIO {name!r}. Choose one of: {', '.join(SCENARIOS)}"
        )
    return name


def active_scenario() -> dict:
    scenario = SCENARIOS[active_scenario_name()]
    overrides = dict(scenario["settings"])
    if "LAB_VIEWS_MODULE" not in overrides:
        overrides["LAB_VIEWS_MODULE"] = scenario["views"]
    return {**scenario, "settings": overrides}
