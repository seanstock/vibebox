from flask import Flask, render_template
import os

# Import tool blueprints directly
from tools.image_utils.routes import image_utils_bp, TOOL_META as image_utils_meta
from tools.print_optimizer.routes import print_optimizer_bp, TOOL_META as print_optimizer_meta
from tools.chaosgraph.routes import chaosgraph_bp, TOOL_META as chaosgraph_meta
from tools.runic.routes import runic_bp, TOOL_META as runic_meta
from tools.subvision.routes import subvision_bp, TOOL_META as subvision_meta

# Create Flask app
app = Flask(__name__, template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Register blueprints
app.register_blueprint(image_utils_bp)
app.register_blueprint(print_optimizer_bp)
app.register_blueprint(chaosgraph_bp)
app.register_blueprint(runic_bp)
app.register_blueprint(subvision_bp)

# Tool metadata
TOOLS = [
    image_utils_meta,
    print_optimizer_meta,
    chaosgraph_meta,
    runic_meta,
    subvision_meta
]

# Add tools list to all template renders
@app.context_processor
def inject_tools():
    return dict(tools=TOOLS)

@app.route('/')
def main():
    # Render the main page template
    return render_template('index.html')

if __name__ == '__main__':
    # Use environment variables or config for host/port in production
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_RUN_PORT', 8083))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host=host, port=port, debug=debug) 