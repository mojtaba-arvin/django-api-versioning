"""Root URLconf depends only on the consumer-owned API adapter."""

from contract_app.versioning import get_urlpatterns

urlpatterns = get_urlpatterns()
