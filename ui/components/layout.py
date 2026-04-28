"""
Reusable layout helpers for a modern, SaaS‑style Streamlit UI.

These helpers only affect presentation (headers, KPI rows, sections)
and are safe to use across all pages without changing core logic.
"""

from typing import List, Dict, Optional, Callable, Tuple

import streamlit as st


def render_page_header(
    title: str,
    subtitle: Optional[str] = None,
    icon: Optional[str] = None,
    right_content: Optional[Callable[[], None]] = None,
) -> None:
    """
    Render a consistent page header with title, subtitle and optional
    right‑aligned content (e.g. date, small stats, actions).
    """
    container = st.container()
    with container:
        col_left, col_right = st.columns([4, 2])

        with col_left:
            title_text = f"{icon} {title}" if icon else title
            st.markdown(f"### {title_text}")
            if subtitle:
                st.markdown(
                    f"<p style='color: var(--text-muted, #64748b); "
                    f"font-size: 0.95rem; margin-top: -0.3rem;'>{subtitle}</p>",
                    unsafe_allow_html=True,
                )

        with col_right:
            if right_content:
                right_content()

    st.markdown("---")


def render_kpi_row(kpis: List[Dict[str, str]]) -> None:
    """
    Render a horizontal row of KPI cards using st.metric.

    Each KPI dict can contain:
      - label: metric label
      - value: main value
      - delta: optional delta text
    """
    if not kpis:
        return

    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            st.metric(
                kpi.get("label", ""),
                kpi.get("value", ""),
                delta=kpi.get("delta"),
            )


def section_title(title: str, description: Optional[str] = None, icon: Optional[str] = None) -> None:
    """Render a section title with optional description."""
    title_text = f"{icon} {title}" if icon else title
    st.markdown(f"#### {title_text}")
    if description:
        st.markdown(
            f"<p style='color: var(--text-muted, #64748b); font-size: 0.9rem;'>{description}</p>",
            unsafe_allow_html=True,
        )


def render_info_strip(
    items: List[Tuple[str, str]],
) -> None:
    """
    Horizontal strip of compact info chips (title + short body).
    Each item is (title, description).
    """
    if not items:
        return
    st.markdown('<div class="info-strip">', unsafe_allow_html=True)
    cols = st.columns(len(items))
    for col, (title, body) in zip(cols, items):
        with col:
            st.markdown(
                f'<div class="info-chip">'
                f'<span class="info-chip-title">{title}</span>'
                f'<p class="info-chip-body">{body}</p>'
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def card_container() -> st.delta_generator.DeltaGenerator:
    """
    Return a container that visually behaves like a 'card'.
    Styling is mostly handled by global CSS; this helper is for semantics.
    Usage:

        with card_container():
            st.markdown("Content")
    """
    return st.container()

