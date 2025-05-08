import cv2
import numpy as np
import os
from io import BytesIO

def process_image(
    img_bytes, angle_x=0, angle_y=0, angle_z=0, scale=1.0, z_offset_factor=1.0,
    shadow_enabled=True, shadow_opacity=0.5, shadow_blur=15, 
    shadow_offset_x=10, shadow_offset_y=10, shadow_color_bgr=(0,0,0)
):
    """
    Apply 3D perspective transformation and shadow to an image.
    
    Parameters:
    - img_bytes: Raw image bytes
    - angle_x, angle_y, angle_z: Rotation angles in degrees
    - scale: Scale factor for the output
    - z_offset_factor: Controls perspective intensity
    - shadow_enabled: Whether to add a drop shadow
    - shadow_opacity: Shadow opacity (0-1)
    - shadow_blur: Shadow blur radius in pixels
    - shadow_offset_x, shadow_offset_y: Shadow offset in pixels
    - shadow_color_bgr: Shadow color in BGR format
    
    Returns:
    - Tuple of (result_bytes, error_string)
    """
    try:
        # Read image from bytes
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img is None:
            return None, "Failed to decode the image."
        
        h, w = img.shape[:2]
        
        # Ensure image has alpha channel
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        
        # Convert angles to radians
        ax, ay, az = np.deg2rad(angle_x), np.deg2rad(angle_y), np.deg2rad(angle_z)
        
        # X-axis rotation (pitch)
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(ax), -np.sin(ax)],
            [0, np.sin(ax), np.cos(ax)]
        ])
        
        # Y-axis rotation (yaw)
        Ry = np.array([
            [np.cos(ay), 0, np.sin(ay)],
            [0, 1, 0],
            [-np.sin(ay), 0, np.cos(ay)]
        ])
        
        # Z-axis rotation (roll)
        Rz = np.array([
            [np.cos(az), -np.sin(az), 0],
            [np.sin(az), np.cos(az), 0],
            [0, 0, 1]
        ])
        
        # Combine rotations
        R = Ry @ Rx @ Rz
        
        # Define corner points
        corners = np.array([
            [0, 0, 0],
            [w, 0, 0],
            [w, h, 0],
            [0, h, 0]
        ], dtype=np.float32).T
        
        # Apply rotation
        rotated = R @ corners
        
        # Apply z-offset to push away from camera
        z_offset = z_offset_factor * max(w, h)
        rotated[2, :] += z_offset
        
        # Perspective projection
        f = 1.5 * max(w, h)  # focal length
        K = np.array([
            [f, 0, w/2],
            [0, f, h/2],
            [0, 0, 1]
        ])
        
        proj = (K @ rotated).T
        proj = proj[:, :2] / proj[:, 2:]  # normalize
        
        # Fit on canvas
        proj -= proj.min(0)
        proj *= scale
        proj += 40  # add border
        
        # Create perspective transform matrix
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = proj.astype(np.float32)
        M = cv2.getPerspectiveTransform(src, dst)
        
        # Allocate space for shadow if enabled
        padding = max(abs(shadow_offset_x), abs(shadow_offset_y)) * 2 if shadow_enabled else 0
        canvas_w = int(dst[:, 0].max() + 40 + padding)
        canvas_h = int(dst[:, 1].max() + 40 + padding)
        
        # Apply perspective transformation
        warped = cv2.warpPerspective(
            img, M, (canvas_w, canvas_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0)
        )
        
        # Add shadow if enabled
        if shadow_enabled:
            # Extract alpha channel from warped image
            alpha_mask = warped[:, :, 3].copy()
            
            # Create shadow image (offset from original)
            shadow = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
            
            # Shift alpha for shadow
            M_shadow = np.float32([[1, 0, shadow_offset_x], [0, 1, shadow_offset_y]])
            shifted_alpha = cv2.warpAffine(alpha_mask, M_shadow, (canvas_w, canvas_h))
            
            # Blur the shadow
            blurred_alpha = cv2.GaussianBlur(shifted_alpha, (shadow_blur*2+1, shadow_blur*2+1), 0)
            
            # Apply opacity
            shadow_alpha = (blurred_alpha * shadow_opacity).astype(np.uint8)
            
            # Set shadow color
            shadow[:, :, 0] = shadow_color_bgr[0]  # B
            shadow[:, :, 1] = shadow_color_bgr[1]  # G
            shadow[:, :, 2] = shadow_color_bgr[2]  # R
            shadow[:, :, 3] = shadow_alpha        # A
            
            # Create result image
            result = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
            
            # Alpha compositing (shadow first, then image)
            for y in range(canvas_h):
                for x in range(canvas_w):
                    if shadow[y, x, 3] > 0:
                        result[y, x] = shadow[y, x]
            
            for y in range(canvas_h):
                for x in range(canvas_w):
                    if warped[y, x, 3] > 0:
                        alpha_fg = warped[y, x, 3] / 255.0
                        alpha_bg = result[y, x, 3] / 255.0
                        
                        # Premultiplied alpha compositing
                        for c in range(3):  # BGR channels
                            result[y, x, c] = int(warped[y, x, c] * alpha_fg + 
                                                result[y, x, c] * alpha_bg * (1 - alpha_fg))
                        
                        # New alpha
                        result[y, x, 3] = int(255 * (alpha_fg + alpha_bg * (1 - alpha_fg)))
        else:
            result = warped
        
        # Encode the result to PNG
        _, result_bytes = cv2.imencode('.png', result)
        
        return result_bytes.tobytes(), None
        
    except Exception as e:
        return None, str(e) 