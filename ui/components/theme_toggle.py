"""
Theme toggle component - WORKING VERSION
Provides dark/light theme switching functionality using Streamlit's native features
"""

import streamlit as st
from typing import Optional

class ThemeToggle:
    """Theme toggle component for dark/light mode switching"""

    def __init__(self):
        self.theme_key = "app_theme"
        self.default_theme = "dark"

        # Initialize theme if not set
        if self.theme_key not in st.session_state:
            st.session_state[self.theme_key] = self.default_theme

    def get_current_theme(self) -> str:
        """Get current theme from session state"""
        return st.session_state.get(self.theme_key, self.default_theme)

    def set_theme(self, theme: str):
        """Set current theme in session state"""
        st.session_state[self.theme_key] = theme

    def toggle_theme(self):
        """Toggle between light and dark theme"""
        current = self.get_current_theme()
        new_theme = "dark" if current == "light" else "light"
        self.set_theme(new_theme)

    def render_toggle_button(self, container=None) -> bool:
        """Render theme toggle button - WORKING VERSION"""
        current_theme = self.get_current_theme()

        if container is None:
            container = st

        # Icons and text for button
        if current_theme == "light":
            icon, text = "🌙", "Switch to Dark Mode"
            button_type = "secondary"
        else:
            icon, text = "☀️", "Switch to Light Mode"
            button_type = "primary"

        # Use Streamlit's native button
        if container.button(f"{icon} {text}", key=f"theme_toggle_{id(container)}", type=button_type, use_container_width=True):
            self.toggle_theme()
            st.rerun()
            return True
        
        return False

    def render_sidebar_toggle(self):
        """Render theme toggle in sidebar"""
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🎨 Theme Settings")
            
            current_theme = self.get_current_theme()
            
            # Radio button for theme selection
            theme_options = {"Light Mode": "light", "Dark Mode": "dark"}
            selected_theme_name = st.radio(
                "Choose Theme",
                options=list(theme_options.keys()),
                index=0 if current_theme == "light" else 1,
                key="sidebar_theme_radio",
                horizontal=True
            )
            
            selected_theme = theme_options[selected_theme_name]
            if selected_theme != current_theme:
                self.set_theme(selected_theme)
                st.rerun()

    def render_header_toggle(self):
        """Render theme toggle in header area"""
        col1, col2, col3 = st.columns([6, 1, 1])
        with col3:
            self.render_toggle_button()

    def apply_theme_css(self):
        """Apply theme-specific CSS - ENHANCED VERSION"""
        current_theme = self.get_current_theme()
        
        # Show theme indicator
        if current_theme == "dark":
            st.markdown("🌙 **Dark Theme Active**")
            self._apply_dark_theme()
        else:
            st.markdown("☀️ **Light Theme Active**")
            self._apply_light_theme()

    def _apply_dark_theme(self):
        """Enhanced dark theme CSS"""
        dark_css = """
        <style>
        /* Dark Theme Variables */
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --text-muted: #94a3b8;
            --border-color: #475569;
            --accent-color: #3b82f6;
        }

        /* Main App Background */
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%) !important;
            color: var(--text-primary) !important;
        }

        /* Main Content Area */
        .main .block-container {
            background: rgba(15, 23, 42, 0.95) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 12px !important;
            backdrop-filter: blur(10px) !important;
            box-shadow: 0 8px 32px rgba(15, 23, 42, 0.7) !important;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e293b 0%, #334155 100%) !important;
            border-right: 1px solid var(--border-color) !important;
        }

        section[data-testid="stSidebar"] > div {
            background: transparent !important;
        }

        /* Input Fields */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > select,
        .stNumberInput > div > div > input {
            background: var(--bg-tertiary) !important;
            color: var(--text-primary) !important;
            border-color: var(--border-color) !important;
            border-radius: 8px !important;
        }

        /* Buttons */
        .stButton > button {
            background: var(--bg-tertiary) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
        }

        .stButton > button:hover {
            background: var(--accent-color) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
        }

        /* Primary Button */
        .stButton > button[kind="primary"] {
            background: var(--accent-color) !important;
            color: white !important;
            border: none !important;
        }

        /* Metrics */
        [data-testid="metric-container"] {
            background: var(--bg-secondary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            padding: 12px !important;
        }

        /* Dataframes */
        .stDataFrame {
            background: var(--bg-secondary) !important;
            border-radius: 8px !important;
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary) !important;
        }

        /* Success/Error Messages */
        .stAlert {
            border-radius: 8px !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background: var(--bg-secondary) !important;
        }

        .stTabs [data-baseweb="tab"] {
            color: var(--text-secondary) !important;
        }

        .stTabs [aria-selected="true"] {
            color: var(--accent-color) !important;
        }
        </style>
        """
        st.markdown(dark_css, unsafe_allow_html=True)

    def _apply_light_theme(self):
        """Enhanced light theme CSS"""
        light_css = """
        <style>
        /* Light Theme Variables */
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8fafc;
            --bg-tertiary: #f1f5f9;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #64748b;
            --border-color: #e2e8f0;
            --accent-color: #3b82f6;
        }

        /* Main App Background */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%) !important;
            color: var(--text-primary) !important;
        }

        /* Main Content Area */
        .main .block-container {
            background: rgba(255, 255, 255, 0.95) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 12px !important;
            backdrop-filter: blur(10px) !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%) !important;
            border-right: 1px solid var(--border-color) !important;
        }

        section[data-testid="stSidebar"] > div {
            background: transparent !important;
        }

        /* Input Fields */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > select,
        .stNumberInput > div > div > input {
            background: var(--bg-primary) !important;
            color: var(--text-primary) !important;
            border-color: var(--border-color) !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
        }

        /* Buttons */
        .stButton > button {
            background: var(--bg-primary) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
        }

        .stButton > button:hover {
            background: var(--accent-color) !important;
            color: white !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
        }

        /* Primary Button */
        .stButton > button[kind="primary"] {
            background: var(--accent-color) !important;
            color: white !important;
            border: none !important;
        }

        /* Metrics */
        [data-testid="metric-container"] {
            background: var(--bg-secondary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            padding: 12px !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
        }

        /* Dataframes */
        .stDataFrame {
            background: var(--bg-primary) !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary) !important;
        }

        /* Success/Error Messages */
        .stAlert {
            border-radius: 8px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background: var(--bg-secondary) !important;
            border-radius: 8px !important;
        }

        .stTabs [data-baseweb="tab"] {
            color: var(--text-secondary) !important;
        }

        .stTabs [aria-selected="true"] {
            color: var(--accent-color) !important;
        }
        </style>
        """
        st.markdown(light_css, unsafe_allow_html=True)

    def render_theme_selector(self):
        """Render advanced theme selector with preview"""
        st.markdown("### 🎨 Theme Settings")
        
        current_theme = self.get_current_theme()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Choose Your Theme")
            
            # Theme preview cards
            if st.button("☀️ Light Theme", key="light_theme_btn", 
                        type="primary" if current_theme == "light" else "secondary",
                        use_container_width=True):
                self.set_theme("light")
                st.rerun()
        
        with col2:
            st.markdown("#### ")  # Spacing
            
            if st.button("🌙 Dark Theme", key="dark_theme_btn",
                        type="primary" if current_theme == "dark" else "secondary", 
                        use_container_width=True):
                self.set_theme("dark")
                st.rerun()

# Global instance
theme_toggle = ThemeToggle()

# Convenience functions
def init_theme():
    """Initialize and apply theme at app start"""
    theme = theme_toggle.get_current_theme()
    theme_toggle.apply_theme_css()
    return theme

def get_current_theme() -> str:
    """Get current theme"""
    return theme_toggle.get_current_theme()

def apply_theme() -> str:
    """Apply current theme and return theme name"""
    theme_toggle.apply_theme_css()
    return theme_toggle.get_current_theme()

def render_theme_toggle():
    """Render theme toggle button"""
    return theme_toggle.render_toggle_button()

def render_sidebar_theme_toggle():
    """Render theme toggle in sidebar"""
    theme_toggle.render_sidebar_toggle()

def render_theme_selector():
    """Render advanced theme selector"""
    theme_toggle.render_theme_selector()
