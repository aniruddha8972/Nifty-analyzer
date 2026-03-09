"""
frontend/styles.py — backward compat shim.
All CSS now lives in frontend/design.py.
Old code that calls inject() still works.
"""
from frontend.design import inject, FINANCE_CSS as CSS  # noqa re-export
