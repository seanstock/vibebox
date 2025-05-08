from flask import Blueprint, render_template

# Tool metadata
TOOL_META = {
    "name": "Chaosgraph", 
    "endpoint": "chaosgraph", 
    "desc": "Generate 3-ring spirograph visualizations", 
    "icon": "🌀"
}

# Create a blueprint with templates in this package
chaosgraph_bp = Blueprint(
    'chaosgraph', 
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/chaosgraph'
)

@chaosgraph_bp.route('/')
def index():
    # This tool is client-side only (JavaScript-based)
    return render_template('chaosgraph.html', active_tool='chaosgraph') 