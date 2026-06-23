"""Smoke test: refinement script uses qwen3 via refinement_mode."""

from __future__ import annotations

import os

os.environ["ENRICHMENT_PROVIDER"] = "ollama"
os.environ["OLLAMA_MODEL"] = "llama3.1"
os.environ["OLLAMA_REFINEMENT_MODEL"] = "qwen3"

from importlib import reload

import app.config as config_mod

reload(config_mod)
from app.config import settings
from app.services.ollama_client import _active_model, refinement_mode

assert settings.ollama_model == "llama3.1", settings.ollama_model
assert settings.ollama_refinement_model == "qwen3", settings.ollama_refinement_model
assert _active_model() == "llama3.1"

with refinement_mode():
    assert _active_model() == "qwen3"

print("OK: live model =", settings.ollama_model, "| refinement model =", settings.ollama_refinement_model)
