import sys
import os

site_packages = os.path.join(os.path.dirname(__file__), 'site-packages')
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
