"""
backend/secrets.py
──────────────────
Single source of truth for secrets/config.

Priority order:
  1. Environment variables (Hugging Face Spaces, Railway, Render, etc.)
  2. st.secrets (Streamlit Cloud / local .streamlit/secrets.toml)
  3. None / empty string

HF Spaces — set these in Space Settings → Repository secrets:
  SUPABASE_URL
  SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY
  APP_URL
"""
import os


def _st_secrets(section: str, key: str, default: str = "") -> str:
    try:
        import streamlit as st
        return st.secrets.get(section, {}).get(key, default) or default
    except Exception:
        return default


def get_supabase_url() -> str:
    return (
        os.environ.get("SUPABASE_URL", "") or
        _st_secrets("supabase", "url")
    )


def get_supabase_anon_key() -> str:
    return (
        os.environ.get("SUPABASE_ANON_KEY", "") or
        _st_secrets("supabase", "anon_key")
    )


def get_supabase_service_key() -> str:
    return (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or
        _st_secrets("supabase", "service_role_key")
    )


def get_app_url() -> str:
    return (
        os.environ.get("APP_URL", "") or
        _st_secrets("app", "url")
    )


def has_supabase() -> bool:
    return bool(get_supabase_url() and get_supabase_anon_key())
