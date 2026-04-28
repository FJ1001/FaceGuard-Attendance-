"""
Premium theme module for consistent UI styling across all pages.
"""
import streamlit as st


class PremiumTheme:
    """Premium theme helper for consistent UI components."""
    
    @staticmethod
    def apply_theme():
        """Apply premium theme styling to Streamlit app."""
        st.markdown("""
        <style>
        /* Premium Theme Variables */
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #818cf8;
            --secondary: #8b5cf6;
            --accent: #ec4899;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --info: #3b82f6;
            --text: #1f2937;
            --text-secondary: #6b7280;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
        }
        
        /* Dark mode variables */
        [data-theme="dark"] {
            --text: #f1f5f9;
            --text-secondary: #94a3b8;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --border: #334155;
        }
        
        /* Global styles */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        
        /* Card styling */
        div[data-testid="stMetric"] {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        /* Button styling */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);
        }
        
        /* Input fields */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select {
            border-radius: 12px;
            border: 2px solid var(--border);
            padding: 0.75rem;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus,
        .stSelectbox > div > div > select:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        
        /* Success/Error messages */
        .success-box {
            background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
            border-left: 4px solid var(--success);
            padding: 1rem;
            border-radius: 12px;
            margin: 1rem 0;
        }
        
        .error-box {
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            border-left: 4px solid var(--error);
            padding: 1rem;
            border-radius: 12px;
            margin: 1rem 0;
        }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def theme_button(label, key=None, type="primary", use_container_width=False):
        """Create a styled button."""
        return st.button(
            label,
            key=key,
            type=type,
            use_container_width=use_container_width
        )
    
    @staticmethod
    def theme_input(label, key=None, type="default", placeholder=""):
        """Create a styled text input."""
        return st.text_input(
            label,
            key=key,
            type=type,
            placeholder=placeholder
        )
    
    @staticmethod
    def theme_selectbox(label, options, key=None, index=0):
        """Create a styled selectbox."""
        return st.selectbox(
            label,
            options,
            key=key,
            index=index
        )
    
    @staticmethod
    def theme_metric(label, value, delta=None):
        """Create a styled metric card."""
        return st.metric(
            label=label,
            value=value,
            delta=delta
        )
    
    @staticmethod
    def success_message(message):
        """Display a styled success message."""
        st.markdown(
            f'<div class="success-box"><p style="margin: 0;">✅ {message}</p></div>',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def error_message(message):
        """Display a styled error message."""
        st.markdown(
            f'<div class="error-box"><p style="margin: 0;">❌ {message}</p></div>',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def info_message(message):
        """Display a styled info message."""
        st.info(message)
    
    @staticmethod
    def warning_message(message):
        """Display a styled warning message."""
        st.warning(message)
