"""Run the portal and admin API contracts against the supplied SQL layout."""
import test_admin_api
import test_portal

from app.storage.existing import metadata


class ExistingPortalTests(test_portal.PortalTests):
    persistent_metadata = metadata


class ExistingAdminApiTests(test_admin_api.AdminApiTests):
    persistent_metadata = metadata
