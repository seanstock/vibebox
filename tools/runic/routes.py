from flask import Blueprint, render_template

# Tool metadata used by main app sidebar
TOOL_META = {
    "name": "Runic Life Keeper",  # Friendly name
    "endpoint": "runic",          # Used in URL and template path
    "desc": "MTG life tracker & dice roller (WIP)",  # Short description
    "icon": "🧙"                  # Unicode wizard icon for flair
}

# Blueprint definition
runic_bp = Blueprint(
    'runic',               # Blueprint name
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/runic'
)

@runic_bp.route('/', methods=['GET'])
def index():
    # Render pure client-side interactive template
    return render_template('runic.html', active_tool='runic') 