"""Prompt engineering for GUI code generation."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


FRAMEWORK_INSTRUCTIONS = {
    "customtkinter": """You are an expert CustomTkinter developer.
Rules:
- Import as: import customtkinter as ctk
- Use CTk widgets: CTkFrame, CTkButton, CTkEntry, CTkLabel, CTkComboBox, CTkCheckBox,
  CTkSegmentedButton, CTkTabview, CTkTextbox, CTkScrollableFrame, CTkSlider, CTkSwitch,
  CTkProgressBar, CTkOptionMenu, CTkRadioButton
- Set appearance: ctk.set_appearance_mode("dark") and ctk.set_default_color_theme("blue")
- Main window: ctk.CTk() not tk.Tk()
- Use grid() or pack() layout, never place()
- Use configure(fg_color=...) not bg= for colors
- Font: ("Segoe UI", 13) for labels, ("Consolas", 12) for code/mono
- Support both dark and light modes
- Add proper padding: padx=10, pady=5 minimum
- Use CTkScrollableFrame for content that may overflow
- Include window icon and proper title""",

    "tkinter": """You are an expert Tkinter/ttk developer.
Rules:
- Use ttk themed widgets whenever available: ttk.Button, ttk.Label, ttk.Entry, ttk.Combobox,
  ttk.Treeview, ttk.Notebook, ttk.Frame, ttk.LabelFrame, ttk.Progressbar, ttk.Scale
- Apply a modern theme: sv_ttk (Sun Valley) or use style.theme_use('clam')
- Use grid() for complex layouts, pack() for simple stacking
- Set proper column/row weights for resizing
- Include ttk.Style() configuration for custom appearance
- Use tkinter.filedialog, tkinter.messagebox
- Set minimum window size with minsize()""",

    "pyqt6": """You are an expert PyQt6 developer.
Rules:
- from PyQt6.QtWidgets import *
- from PyQt6.QtCore import Qt, QThread, pyqtSignal
- from PyQt6.QtGui import QFont, QIcon, QPalette, QColor
- Use QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout
- Apply stylesheets with setStyleSheet() for modern look
- Use QThread for background tasks, NEVER block the main thread
- Emit signals for thread-safe UI updates
- Include QMenuBar, QStatusBar, QToolBar where appropriate
- Use QSplitter for resizable panels
- Set windowTitle, resize, and setMinimumSize""",

    "pyside6": """You are an expert PySide6 developer.
Rules:
- from PySide6.QtWidgets import *
- from PySide6.QtCore import Qt, QThread, Signal
- Use Signal instead of pyqtSignal
- Use Slot decorator: @Slot()
- Same layout and widget patterns as PyQt6
- Use QML for declarative UI when appropriate
- Apply Material or Fusion style""",

    "wxpython": """You are an expert wxPython developer.
Rules:
- import wx, wx.adv, wx.lib.agw
- Use wx.BoxSizer, wx.GridBagSizer, wx.FlexGridSizer
- Main frame: wx.Frame with wx.Panel as child
- Use wx.MenuBar, wx.StatusBar, wx.ToolBar
- Bind events: self.Bind(wx.EVT_BUTTON, handler, button)
- Use wx.CallAfter for thread-safe UI updates
- Include wx.FileDialog, wx.MessageDialog
- Set proper sizer flags: wx.ALL | wx.EXPAND""",

    "kivy": """You are an expert Kivy developer.
Rules:
- from kivy.app import App
- from kivy.uix.boxlayout import BoxLayout
- Use .kv language for UI definition when complex
- Use Clock.schedule_once for deferred operations
- Support touch events and multi-touch
- Use dp() for density-independent pixels
- Include proper screen management with ScreenManager""",

    "dearpygui": """You are an expert Dear PyGui developer.
Rules:
- import dearpygui.dearpygui as dpg
- dpg.create_context(), dpg.create_viewport(), dpg.setup_dearpygui()
- Use with dpg.window(), dpg.group(), dpg.child_window()
- Use dpg.add_button, dpg.add_input_text, dpg.add_combo
- Callbacks: callback=lambda s, d: handler(d)
- Use dpg.add_theme for styling
- dpg.show_viewport(), dpg.start_dearpygui(), dpg.destroy_context()""",

    "flet": """You are an expert Flet developer.
Rules:
- import flet as ft
- Main function: def main(page: ft.Page)
- Use ft.Column, ft.Row, ft.Container, ft.Stack
- Widgets: ft.ElevatedButton, ft.TextField, ft.Text, ft.Dropdown
- Update UI: page.update() or control.update()
- Use page.theme_mode = ft.ThemeMode.DARK
- ft.app(target=main) to launch""",

    "nicegui": """You are an expert NiceGUI developer.
Rules:
- from nicegui import ui
- Use ui.button, ui.input, ui.label, ui.select, ui.table
- Layout: ui.row(), ui.column(), ui.card(), ui.expansion()
- Style with Tailwind classes: .classes('w-full p-4')
- Use ui.notify for notifications
- Dark mode: ui.dark_mode()
- ui.run() to start""",

    "streamlit": """You are an expert Streamlit developer.
Rules:
- import streamlit as st
- Use st.columns, st.tabs, st.expander, st.container, st.sidebar
- Widgets: st.button, st.text_input, st.selectbox, st.slider, st.file_uploader
- State: st.session_state for persistence
- Use st.cache_data and st.cache_resource for performance
- Use st.form for grouped inputs
- Charts: st.plotly_chart, st.altair_chart""",

    "gradio": """You are an expert Gradio developer.
Rules:
- import gradio as gr
- Use gr.Blocks() as the main container
- Layout: gr.Row(), gr.Column(), gr.Tab(), gr.Accordion()
- Inputs: gr.Textbox, gr.Slider, gr.Dropdown, gr.Checkbox, gr.File
- Outputs: gr.Textbox, gr.Image, gr.Plot, gr.HTML, gr.Dataframe
- Connect with .click(), .change(), .submit()
- Use gr.State for stateful apps""",

    "html_css_js": """You are an expert web developer.
Rules:
- Use semantic HTML5: header, nav, main, section, article, footer
- Modern CSS: flexbox, grid, custom properties, media queries
- Vanilla JavaScript ES6+ or include CDN links for frameworks
- Mobile-first responsive design
- Include dark mode support with prefers-color-scheme
- Use CSS variables for theming
- Accessibility: ARIA labels, keyboard navigation, focus management
- Include meta viewport tag""",
}

STYLE_MODIFIERS = {
    "modern": "Use a clean, modern design with rounded corners, subtle shadows, smooth transitions, and generous whitespace.",
    "minimal": "Use a minimalist design with maximum whitespace, thin borders, monochrome palette, and only essential elements.",
    "material": "Follow Material Design 3 guidelines: elevated surfaces, tonal color system, dynamic color, motion.",
    "glassmorphism": "Use glassmorphism: frosted glass effect, transparency, blur, soft borders, layered elements.",
    "retro": "Use a retro aesthetic: pixel-like elements, neon colors on dark background, CRT-style effects.",
    "corporate": "Professional corporate style: clean lines, neutral colors, data-focused, dashboard-like layout.",
    "gaming": "Gaming UI style: dark theme, neon accents, angular elements, tech-inspired typography.",
    "nature": "Organic design: earth tones, rounded organic shapes, leaf/nature motifs, calming palette.",
    "gradient": "Heavy use of gradients: background gradients, button gradients, text gradients, aurora effects.",
    "flat": "Flat design: no shadows, no gradients, solid bright colors, clean geometric shapes.",
    "neumorphism": "Neumorphic design: soft shadows, embossed/debossed elements, monochrome with subtle depth.",
    "brutalist": "Brutalist web design: raw, bold, unconventional layouts, stark contrasts, experimental.",
}

COMPONENT_CATALOG = {
    "sidebar": "collapsible sidebar navigation with icons and labels",
    "navbar": "top navigation bar with logo, links, and user menu",
    "toolbar": "horizontal toolbar with icon buttons and separators",
    "status_bar": "bottom status bar with sections for info display",
    "tab_view": "tabbed content area with multiple switchable panels",
    "tree_view": "hierarchical tree view for file/data browsing",
    "table": "data table with sorting, filtering, and pagination",
    "form": "input form with labels, validation, and submit button",
    "card": "content card with header, body, and optional footer",
    "modal": "modal dialog overlay with title, content, and action buttons",
    "toast": "non-blocking notification popup (success/error/warning/info)",
    "search_bar": "search input with autocomplete/suggestions dropdown",
    "file_browser": "file open/save dialog or embedded file browser",
    "settings_panel": "settings/preferences panel with grouped options",
    "dashboard": "dashboard layout with metric cards and chart placeholders",
    "chat_widget": "chat interface with message bubbles and input",
    "code_editor": "code editor with syntax highlighting and line numbers",
    "image_viewer": "image display with zoom, pan, and basic controls",
    "progress_tracker": "multi-step progress indicator / wizard",
    "split_view": "resizable split panel (horizontal or vertical)",
    "accordion": "collapsible accordion sections",
    "breadcrumb": "breadcrumb navigation trail",
    "color_picker": "color selection widget with preview",
    "date_picker": "calendar-based date selection",
    "drag_drop_area": "drag and drop file upload area",
    "context_menu": "right-click context menu",
    "ribbon": "Microsoft-style ribbon toolbar with grouped actions",
    "kanban": "kanban board with draggable cards across columns",
    "timeline": "vertical or horizontal timeline display",
    "terminal": "embedded terminal/console output display",
}


def get_system_instruction(framework: str) -> str:
    """Get the system instruction for a specific framework."""
    base = FRAMEWORK_INSTRUCTIONS.get(framework, FRAMEWORK_INSTRUCTIONS["customtkinter"])
    return f"""{base}

CRITICAL OUTPUT RULES:
1. Return ONLY the complete, runnable Python code
2. Include ALL imports at the top
3. Include if __name__ == '__main__': guard
4. Use type hints on all function signatures
5. Include docstrings for classes and public methods
6. Handle window close events gracefully
7. Use threading for any operation > 100ms
8. Add proper error handling with try/except
9. Make the window resizable with proper weight configuration
10. Use relative sizing, not absolute pixel values where possible
11. Support HiDPI/scaling
12. Wrap the code in a single ```python code fence
13. No explanatory text outside the code fence"""


def build_generation_prompt(
    description: str,
    framework: str = "customtkinter",
    style: str = "modern",
    components: Optional[list[str]] = None,
    existing_code: Optional[str] = None,
) -> str:
    """Build a structured prompt for GUI generation."""
    parts: list[str] = []
    parts.append(f"Generate a complete, runnable {framework} GUI application.")
    parts.append(f"\nDESCRIPTION:\n{description}")

    if style in STYLE_MODIFIERS:
        parts.append(f"\nSTYLE: {STYLE_MODIFIERS[style]}")

    if components:
        comp_desc = []
        for comp in components:
            if comp in COMPONENT_CATALOG:
                comp_desc.append(f"- {comp}: {COMPONENT_CATALOG[comp]}")
            else:
                comp_desc.append(f"- {comp}")
        parts.append(f"\nREQUIRED COMPONENTS:\n" + "\n".join(comp_desc))

    if existing_code:
        parts.append(f"\nEXISTING CODE TO BUILD UPON:\n```python\n{existing_code}\n```")
        parts.append("Integrate new features into this existing code. Preserve all current functionality.")

    parts.append("\nOUTPUT: Return the complete runnable code in a single ```python code fence.")
    return "\n".join(parts)


def build_refinement_prompt(
    feedback: str,
    current_code: str,
    framework: str = "customtkinter",
) -> str:
    """Build a prompt for refining existing GUI code."""
    return f"""Modify this {framework} GUI application based on the feedback below.

CURRENT CODE:
```python
{current_code}
```

FEEDBACK / CHANGES REQUESTED:
{feedback}

RULES:
- Preserve ALL existing functionality unless explicitly asked to remove it
- Keep the same code structure and patterns
- Only change what the feedback requires
- Return the COMPLETE updated code in a single ```python code fence
- Do not remove features or simplify unless asked"""


def build_component_prompt(
    component_type: str,
    current_code: str,
    placement: str = "",
    framework: str = "customtkinter",
) -> str:
    """Build a prompt for adding a component to existing code."""
    comp_desc = COMPONENT_CATALOG.get(component_type, component_type)
    placement_note = f"\nPlacement: {placement}" if placement else ""

    return f"""Add a {component_type} component to this {framework} GUI application.

COMPONENT: {comp_desc}{placement_note}

CURRENT CODE:
```python
{current_code}
```

RULES:
- Integrate the component naturally into the existing layout
- Match the existing code style and patterns
- Wire up events and callbacks appropriately
- Return the COMPLETE updated code in a single ```python code fence"""


def build_layout_prompt(
    layout_type: str,
    panel_count: int = 2,
    framework: str = "customtkinter",
) -> str:
    """Build a prompt for generating a layout skeleton."""
    return f"""Generate a {framework} application with a {layout_type} layout.

LAYOUT: {layout_type} with {panel_count} panels
- Each panel should have placeholder content (labels indicating panel purpose)
- Include proper sizing, weights, and resize behavior
- Add minimum size constraints
- Make panels distinguishable with subtle background color differences

Return the complete runnable code in a single ```python code fence."""


def build_clone_prompt(
    target_app: str,
    framework: str = "customtkinter",
    style: str = "modern",
) -> str:
    """Build a prompt for cloning the look of a known application."""
    style_mod = STYLE_MODIFIERS.get(style, "")
    return f"""Create a {framework} GUI that mimics the layout and design of: {target_app}

Focus on:
- Overall layout structure (sidebar, toolbar, content area, status bar, etc.)
- General proportions and spacing
- Color scheme and typography feel
- Key UI elements and their arrangement
{f'Style modifier: {style_mod}' if style_mod else ''}

Do NOT replicate proprietary features or logos. Create a clean, original implementation
that captures the general look and feel.

Return the complete runnable code in a single ```python code fence."""


def build_multifile_prompt(
    description: str,
    file_structure: dict[str, str],
    framework: str = "customtkinter",
) -> str:
    """Build a prompt for generating a multi-file GUI project."""
    files_desc = "\n".join(f"- {name}: {desc}" for name, desc in file_structure.items())
    return f"""Generate a multi-file {framework} GUI application.

DESCRIPTION: {description}

FILE STRUCTURE:
{files_desc}

RULES:
- Each file should be in its own ```python code fence with the filename as a comment on the first line
- Use relative imports between modules
- main.py should be the entry point
- Separate UI, logic, and data layers
- Include __init__.py for packages

Return ALL files, each in a separate code fence with # filename.py as the first line."""


def get_component_list() -> dict[str, str]:
    """Return the full component catalog for UI display."""
    return dict(COMPONENT_CATALOG)


def get_style_list() -> dict[str, str]:
    """Return available styles for UI display."""
    return dict(STYLE_MODIFIERS)


def get_framework_list() -> dict[str, str]:
    """Return supported frameworks for UI display."""
    from .config import FRAMEWORK_DISPLAY
    return dict(FRAMEWORK_DISPLAY)
