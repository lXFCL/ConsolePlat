# AI Providers And Blue Theme Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore multi-provider AI edit settings in the Settings page, migrate old single-provider settings safely, wire AI Edit and Publish flows to the default provider, and shift the app theme back to a blue-accent visual system.

**Architecture:** Extend `AppSettings` with an encrypted provider list plus a default provider id, keep backward compatibility by migrating existing single-provider fields on load, and update UI pages to read/write the default provider instead of the legacy singleton fields. Theme recovery stays token-based inside `theme.py` so layout logic remains unchanged.

**Tech Stack:** Python, PyQt5, dataclasses, DPAPI-backed settings storage, pytest

---
