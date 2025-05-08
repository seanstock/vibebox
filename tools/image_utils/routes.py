from flask import Blueprint, request, render_template, send_file
import os
from .image_processor import process_image

# Tool metadata - this is used by the main app
TOOL_META = {
    "name": "Image Utils", 
    "endpoint": "image_utils", 
    "desc": "3D perspective and shadow image tool", 
    "icon": "📷"
}

# Create a blueprint with templates in this package
image_utils_bp = Blueprint(
    'image_utils', 
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/image_utils'
)

@image_utils_bp.route('/', methods=['GET', 'POST'])
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
                angle_x = float(request.form.get('angle_x', 0))
                angle_y = float(request.form.get('angle_y', 0))
                angle_z = float(request.form.get('angle_z', 0))
                scale = float(request.form.get('scale', 1))
                z_offset_factor = float(request.form.get('z_offset_factor', 1))
                shadow_enabled = 'shadow_enabled' in request.form
                shadow_opacity = float(request.form.get('shadow_opacity', 0.5))
                shadow_blur = int(request.form.get('shadow_blur', 15))
                shadow_offset_x = int(request.form.get('shadow_offset_x', 10))
                shadow_offset_y = int(request.form.get('shadow_offset_y', 10))
                color_str = request.form.get('shadow_color_bgr', '0,0,0')
                shadow_color_bgr = tuple(int(x) for x in color_str.split(','))
                
                # Define result file path (relative to app root)
                result_path = 'results/image_utils_result.png'

                result_bytes, err = process_image(
                    img_bytes, angle_x, angle_y, angle_z, scale, z_offset_factor,
                    shadow_enabled, shadow_opacity, shadow_blur, shadow_offset_x, shadow_offset_y, shadow_color_bgr
                )
                
                if err:
                    error = err
                else:
                    # Save the result temporarily
                    with open(result_path, 'wb') as out:
                        out.write(result_bytes)
                    img_url = '/image_utils/result' # Use a route to serve the image
            except Exception as e:
                error = f"An error occurred: {e}"
                
    return render_template('image_utils.html', error=error, img_url=img_url, active_tool='image_utils')

@image_utils_bp.route('/result')
def serve_result():
    # Serve the temporarily saved result file
    # Note: This simple approach saves only one result at a time.
    # For multi-user or persistent results, a different storage mechanism is needed.
    result_path = 'results/image_utils_result.png'
    if os.path.exists(result_path):
        return send_file(result_path, mimetype='image/png', as_attachment=False)
    else:
        return "Result image not found.", 404 