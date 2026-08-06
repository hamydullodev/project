"""Design tokens: color palette, spacing, radii, gradients, typography.

Shared "AI product family" palette — the same tokens used by Avia AI and
UzLaw AI. Custom CSS (:mod:`app.ui.styles`) reads these instead of
hard-coding colors, so all products stay visually consistent and the
light/dark toggle only needs to swap CSS custom properties, not every
component.
"""

from __future__ import annotations

# Light (default) palette
BACKGROUND = "#F8FAFC"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F1F5F9"
BORDER = "#E5E7EB"
TEXT_PRIMARY = "#0F172A"
TEXT_MUTED = "#64748B"

# Dark palette (toggled via [data-theme="dark"])
BACKGROUND_DARK = "#0B1220"
SURFACE_DARK = "#111827"
SURFACE_ALT_DARK = "#1A2436"
BORDER_DARK = "rgba(255, 255, 255, 0.08)"
TEXT_PRIMARY_DARK = "#F1F5F9"
TEXT_MUTED_DARK = "#94A3B8"

PRIMARY = "#2563EB"
SECONDARY = "#3B82F6"
ACCENT = "#38BDF8"
PRIMARY_SOFT = "rgba(37, 99, 235, 0.10)"
ACCENT_GRADIENT = "linear-gradient(135deg, #2563EB 0%, #38BDF8 100%)"

SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#EF4444"

RADIUS_SM = "10px"
RADIUS_MD = "16px"
RADIUS_LG = "24px"

SHADOW_SM = "0 1px 2px rgba(15, 23, 42, 0.06)"
SHADOW_MD = "0 4px 16px rgba(15, 23, 42, 0.08)"
SHADOW_LG = "0 12px 32px rgba(15, 23, 42, 0.12)"

SPACE_SM = "0.5rem"
SPACE_MD = "1rem"
SPACE_LG = "1.5rem"

FONT_STACK = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
