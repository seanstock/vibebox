from flask import Blueprint, request, render_template, send_file
import uuid
import os
from .print_processor import optimize_for_print

# Tool metadata
TOOL_META = {
    "name": "Print Optimizer", 
    "endpoint": "print_optimizer", 
    "desc": "Optimize digital images for print", 
    "icon": "🖨️"
}

# Create a blueprint with templates in this package
print_optimizer_bp = Blueprint(
    'print_optimizer', 
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/print_optimizer'
)

@print_optimizer_bp.route('/', methods=['GET', 'POST'])
def index():
    error = None
    img_url = None
    if request.method == 'POST':
        f = request.files.get('image')
        if not f:
            error = 'No image uploaded.'
        else:
            try:
                img_bytes = f.read()
                color_depth = int(request.form.get('color_depth', 4))
                
                result_bytes, err = optimize_for_print(
                    img_bytes, color_depth
                )
                
                if err:
                    error = err
                else:
                    result_id = str(uuid.uuid4())
                    # Save to the results directory
                    output_path = f'results/print_result_{result_id}.png' 
                    with open(output_path, 'wb') as out:
                        out.write(result_bytes)
                    img_url = f'/print_optimizer/result/{result_id}' # Route to serve this specific result
            except Exception as e:
                error = f"An error occurred: {e}"
                
    return render_template('print_optimizer.html', error=error, img_url=img_url, active_tool='print_optimizer')

@print_optimizer_bp.route('/result/<result_id>')
def serve_result(result_id):
    # Validate result_id to prevent path traversal
    if not result_id or not all(c.isalnum() or c == '-' for c in result_id):
        return "Invalid result ID", 400
    
    output_path = f'results/print_result_{result_id}.png'
    if os.path.exists(output_path):
        return send_file(output_path, mimetype='image/png', as_attachment=False)
    else:
        # Consider cleaning up old files here eventually
        return "Result image not found or expired.", 404 