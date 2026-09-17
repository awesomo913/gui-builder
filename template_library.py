"""Built-in GUI template library for quick-start generation."""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Template:
    """A GUI template definition."""
    id: str
    name: str
    description: str
    category: str
    framework: str
    tags: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    prompt: str = ""
    thumbnail: str = ""
    difficulty: str = "beginner"


CATEGORIES = {
    "starter": "Starter Templates",
    "dashboard": "Dashboards & Analytics",
    "editor": "Editors & Tools",
    "data": "Data & Database",
    "media": "Media & Content",
    "utility": "Utilities & System",
    "business": "Business & Productivity",
    "game": "Games & Interactive",
    "ai": "AI & ML Tools",
    "social": "Social & Communication",
}


_TEMPLATES: list[Template] = [
    Template(
        id="blank_window",
        name="Blank Window",
        description="Empty window with proper setup, menu bar, and status bar",
        category="starter",
        framework="any",
        tags=["blank", "starter", "minimal"],
        components=["status_bar"],
        difficulty="beginner",
        prompt="Create a blank application window with a menu bar (File > Exit, Help > About), a status bar at the bottom showing 'Ready', and proper window close handling. The main content area should be empty and ready for widgets.",
    ),
    Template(
        id="sidebar_app",
        name="Sidebar Navigation App",
        description="App with collapsible sidebar, content area, and toolbar",
        category="starter",
        framework="any",
        tags=["sidebar", "navigation", "layout"],
        components=["sidebar", "toolbar", "status_bar"],
        difficulty="beginner",
        prompt="Create an application with a collapsible left sidebar (250px wide) containing navigation buttons with icons, a top toolbar with common actions, a main content area that shows different content per sidebar selection, and a bottom status bar. Include a toggle button to collapse/expand the sidebar.",
    ),
    Template(
        id="tab_app",
        name="Tabbed Application",
        description="Multi-tab application with settings and about tabs",
        category="starter",
        framework="any",
        tags=["tabs", "multi-panel", "layout"],
        components=["tab_view", "status_bar", "form"],
        difficulty="beginner",
        prompt="Create a tabbed application with 4 tabs: Home (welcome message and quick actions), Data (placeholder table), Settings (grouped preferences with toggles and dropdowns), and About (app info with version). Include a menu bar and status bar.",
    ),
    Template(
        id="dashboard_analytics",
        name="Analytics Dashboard",
        description="Dashboard with metric cards, charts, and data table",
        category="dashboard",
        framework="any",
        tags=["dashboard", "analytics", "metrics", "charts"],
        components=["dashboard", "card", "table", "navbar"],
        difficulty="intermediate",
        prompt="Create an analytics dashboard with: 4 metric cards at top (Total Users, Revenue, Orders, Conversion Rate with values and trend arrows), a row of 2 chart placeholder areas (line chart and bar chart), and a data table at the bottom with sample data, sorting, and search. Include a top navbar with app title and date range selector.",
    ),
    Template(
        id="dashboard_system",
        name="System Monitor",
        description="Real-time system monitoring dashboard",
        category="dashboard",
        framework="any",
        tags=["system", "monitor", "real-time", "metrics"],
        components=["dashboard", "card", "progress_tracker"],
        difficulty="intermediate",
        prompt="Create a system monitor dashboard showing: CPU usage (gauge + history), RAM usage (bar + details), Disk usage per partition (progress bars), Network I/O (live counters), Running processes list with PID and memory. Update values every 2 seconds using threading. Include psutil for real data.",
    ),
    Template(
        id="text_editor",
        name="Text Editor",
        description="Full text editor with syntax highlighting and file operations",
        category="editor",
        framework="any",
        tags=["editor", "text", "file", "syntax"],
        components=["code_editor", "toolbar", "status_bar", "search_bar"],
        difficulty="intermediate",
        prompt="Create a text editor with: menu bar (File: New/Open/Save/Save As/Exit, Edit: Undo/Redo/Cut/Copy/Paste/Find, View: Word Wrap/Font Size/Theme), toolbar with icon buttons, main text area with line numbers, find/replace bar (Ctrl+F), status bar showing line:col count and file encoding. Support multiple tabs for open files.",
    ),
    Template(
        id="code_editor",
        name="Code Editor",
        description="Code editor with syntax highlighting and terminal",
        category="editor",
        framework="any",
        tags=["code", "ide", "terminal", "syntax"],
        components=["code_editor", "terminal", "tree_view", "split_view"],
        difficulty="advanced",
        prompt="Create a code editor with: left file tree panel (collapsible), main code editing area with line numbers and monospace font, bottom terminal/output panel (resizable split), tab bar for multiple open files, status bar showing language and cursor position. Include basic syntax highlighting for Python using tag-based coloring.",
    ),
    Template(
        id="database_viewer",
        name="Database Browser",
        description="SQLite database viewer with query editor",
        category="data",
        framework="any",
        tags=["database", "sql", "table", "query"],
        components=["tree_view", "table", "code_editor", "split_view"],
        difficulty="intermediate",
        prompt="Create a SQLite database browser with: left panel showing tables/views in a tree, main area split between a SQL query editor (top) and results table (bottom), toolbar with Open DB, Execute Query, Export buttons. Include sample database creation on first run. Show column types and row count in the tree view.",
    ),
    Template(
        id="image_viewer",
        name="Image Viewer",
        description="Image viewer with thumbnails and basic editing",
        category="media",
        framework="any",
        tags=["image", "viewer", "gallery", "photo"],
        components=["image_viewer", "toolbar", "sidebar"],
        difficulty="intermediate",
        prompt="Create an image viewer with: toolbar (Open, Zoom In/Out, Fit to Window, Rotate, Previous/Next), main image display area with zoom and scroll, left thumbnail strip showing all images in folder, status bar showing image dimensions and file size. Support common formats (PNG, JPG, GIF, BMP). Use PIL/Pillow for image loading.",
    ),
    Template(
        id="file_manager",
        name="File Manager",
        description="Dual-pane file manager with common operations",
        category="utility",
        framework="any",
        tags=["files", "manager", "explorer", "dual-pane"],
        components=["tree_view", "table", "split_view", "toolbar", "breadcrumb"],
        difficulty="advanced",
        prompt="Create a dual-pane file manager with: toolbar (Back/Forward/Up/Home/Refresh), address/breadcrumb bar, dual pane view with file listings showing Name/Size/Date/Type, right-click context menu (Open/Copy/Move/Delete/Rename/Properties), status bar showing item count and disk space. Support column sorting and both icon and list views.",
    ),
    Template(
        id="calculator",
        name="Scientific Calculator",
        description="Calculator with basic and scientific modes",
        category="utility",
        framework="any",
        tags=["calculator", "math", "scientific"],
        components=["form"],
        difficulty="beginner",
        prompt="Create a scientific calculator with: display showing current expression and result, basic operations (+, -, *, /, =, C, CE, backspace), scientific functions (sin, cos, tan, log, ln, sqrt, x^2, x^y, pi, e), memory operations (MC, MR, M+, M-), history panel showing recent calculations. Use eval() safely with ast.literal_eval for parsing.",
    ),
    Template(
        id="todo_app",
        name="Todo / Task Manager",
        description="Task manager with categories, priorities, and due dates",
        category="business",
        framework="any",
        tags=["todo", "tasks", "productivity", "kanban"],
        components=["table", "form", "sidebar", "modal"],
        difficulty="intermediate",
        prompt="Create a task manager with: sidebar with categories (All, Today, Important, Completed), main list showing tasks with checkbox, title, priority badge, due date, add task form (title, description, priority, due date, category), edit/delete via right-click, persist tasks to JSON file. Include drag-to-reorder and filter/sort options.",
    ),
    Template(
        id="chat_app",
        name="Chat Interface",
        description="Chat UI with message bubbles and conversation list",
        category="social",
        framework="any",
        tags=["chat", "messaging", "conversation"],
        components=["chat_widget", "sidebar", "search_bar"],
        difficulty="intermediate",
        prompt="Create a chat interface with: left sidebar listing conversations with avatar, name, and last message preview, main chat area with message bubbles (sent right-aligned blue, received left-aligned gray), message input bar with send button and emoji picker placeholder, top bar showing current contact name and status. Include timestamps on messages.",
    ),
    Template(
        id="settings_preferences",
        name="Settings Panel",
        description="Rich settings panel with multiple sections",
        category="utility",
        framework="any",
        tags=["settings", "preferences", "config"],
        components=["settings_panel", "accordion", "form"],
        difficulty="beginner",
        prompt="Create a settings panel with sections: General (theme toggle dark/light, language dropdown, font size slider), Appearance (color accent picker, layout options, animation toggle), Notifications (enable/disable, sound, email), Privacy (data collection toggle, clear data button, export data), About (version, update check, licenses). Each section collapsible. Include Save/Cancel/Reset buttons.",
    ),
    Template(
        id="api_tester",
        name="API Tester",
        description="REST API testing tool like a mini Postman",
        category="utility",
        framework="any",
        tags=["api", "rest", "testing", "http"],
        components=["form", "tab_view", "code_editor", "table"],
        difficulty="advanced",
        prompt="Create a REST API tester with: URL bar with method dropdown (GET/POST/PUT/DELETE/PATCH), tabbed request area (Params, Headers, Body with JSON editor, Auth), Send button with loading indicator, response panel showing status code, time, size, response body with JSON formatting, response headers tab. Include history of recent requests and ability to save/load collections.",
    ),
    Template(
        id="kanban_board",
        name="Kanban Board",
        description="Drag-and-drop kanban board with swimlanes",
        category="business",
        framework="any",
        tags=["kanban", "project", "agile", "board"],
        components=["kanban", "card", "modal"],
        difficulty="advanced",
        prompt="Create a kanban board with columns: Backlog, Todo, In Progress, Review, Done. Each column shows cards with title, description preview, assignee avatar, priority color badge, and due date. Include: add card button per column, edit card modal, drag indication (cards can be moved between columns via buttons since true drag-drop is framework-dependent), column card count, board title and filter options.",
    ),
    Template(
        id="music_player",
        name="Music Player",
        description="Audio player with playlist and visualizer placeholder",
        category="media",
        framework="any",
        tags=["music", "audio", "player", "playlist"],
        components=["sidebar", "progress_tracker", "toolbar"],
        difficulty="intermediate",
        prompt="Create a music player UI with: left playlist panel (add files, reorder, remove), main area with album art placeholder and track info (title, artist, album), playback controls (previous, play/pause, next, shuffle, repeat), progress bar with time display, volume slider, bottom now-playing bar. Use tkinter/pygame for actual audio if framework supports it, otherwise focus on the UI.",
    ),
    Template(
        id="ai_chat",
        name="AI Chat Interface",
        description="ChatGPT/Claude-style AI conversation interface",
        category="ai",
        framework="any",
        tags=["ai", "chat", "llm", "conversation"],
        components=["chat_widget", "sidebar", "settings_panel"],
        difficulty="intermediate",
        prompt="Create an AI chat interface like ChatGPT/Claude with: left sidebar with conversation history (new chat, list of past chats, delete), main chat area with markdown-rendered messages (user and assistant with different styling), message input with multiline support and send button, model selector dropdown, temperature slider, top bar with conversation title. Include code block rendering with copy button in messages.",
    ),
    Template(
        id="form_builder",
        name="Form Builder",
        description="Drag-and-drop form builder with preview",
        category="editor",
        framework="any",
        tags=["form", "builder", "drag-drop", "wysiwyg"],
        components=["form", "sidebar", "split_view", "drag_drop_area"],
        difficulty="advanced",
        prompt="Create a form builder with: left palette of form widgets (text input, textarea, dropdown, checkbox, radio, date picker, file upload, section header), center design canvas showing the form layout, right properties panel for selected widget (label, placeholder, required, validation rules), bottom preview/JSON toggle showing the form output. Include add/remove/reorder form fields.",
    ),
    Template(
        id="markdown_editor",
        name="Markdown Editor",
        description="Side-by-side markdown editor with live preview",
        category="editor",
        framework="any",
        tags=["markdown", "editor", "preview", "writing"],
        components=["code_editor", "split_view", "toolbar"],
        difficulty="intermediate",
        prompt="Create a markdown editor with: toolbar (Bold, Italic, Heading, Link, Image, Code, List, Quote, Table, Preview toggle), split view with editor on left and rendered preview on right, line numbers in editor, file open/save, export to HTML, word/character count in status bar. Parse markdown to HTML for the preview pane.",
    ),
]


def get_all_templates() -> list[Template]:
    """Return all available templates."""
    return list(_TEMPLATES)


def get_templates_by_category(category: str) -> list[Template]:
    """Return templates filtered by category."""
    return [t for t in _TEMPLATES if t.category == category]


def get_templates_by_framework(framework: str) -> list[Template]:
    """Return templates compatible with a framework."""
    return [t for t in _TEMPLATES if t.framework in (framework, "any")]


def get_template_by_id(template_id: str) -> Optional[Template]:
    """Find a template by its ID."""
    for t in _TEMPLATES:
        if t.id == template_id:
            return t
    return None


def search_templates(query: str) -> list[Template]:
    """Search templates by name, description, or tags."""
    query_lower = query.lower()
    results: list[Template] = []
    for t in _TEMPLATES:
        score = 0
        if query_lower in t.name.lower():
            score += 3
        if query_lower in t.description.lower():
            score += 2
        if any(query_lower in tag for tag in t.tags):
            score += 1
        if score > 0:
            results.append(t)
    return results


def get_categories() -> dict[str, str]:
    """Return all template categories."""
    return dict(CATEGORIES)


def get_template_count() -> int:
    """Return total number of templates."""
    return len(_TEMPLATES)
