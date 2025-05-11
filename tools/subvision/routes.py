from flask import Blueprint, render_template

# Tool metadata
TOOL_META = {
    "name": "Subvision", 
    "endpoint": "subvision", 
    "desc": "Flappy submarine game (WIP)", 
    "icon": "🐠"
}

# Blueprint definition
subvision_bp = Blueprint(
    'subvision', 
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/subvision'
)

@subvision_bp.route('/')
def index():
    # Renders the HTML containing the canvas and game logic
    return render_template('subvision.html', active_tool='subvision') 