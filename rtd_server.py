"""Compatibility entry point. Keep existing scripts and imports working."""
from rtd.config import ROOT, STARTERS
from rtd.common import ProtocolError, compact
from rtd.storage.store import Store
from rtd.services.api import API
from rtd.transport.http import handler_for
from rtd.app import main

if __name__ == '__main__':
    main()
