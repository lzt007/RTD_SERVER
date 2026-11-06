"""Authenticate HTTP fixtures without reading or publishing deployment credentials."""
import base64
import secrets
from unittest.mock import patch


def credentials(testcase):
    password = secrets.token_urlsafe(24)
    environment = patch.dict('os.environ', RTD_ADMIN_PASSWORD=password)
    environment.start()
    testcase.addCleanup(environment.stop)
    encoded = base64.b64encode(('admin:' + password).encode()).decode()
    return {'Authorization': 'Basic ' + encoded}
