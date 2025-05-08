import cv2
import numpy as np
from io import BytesIO
from scipy.ndimage import convolve, label, find_objects

def _reduce_colors_ref(img_bgr, r_bit, g_bit, b_bit):
    """Reduce the number of colors in a BGR image using bit manipulation."""
    # Ensure integer inputs for bit manipulation
    r_bit, g_bit, b_bit = int(r_bit), int(g_bit), int(b_bit)
    
    r = np.right_shift(img_bgr[..., 2], 8 - r_bit) # R is at index 2 in BGR
    r = np.left_shift(r, 8 - r_bit)
    g = np.right_shift(img_bgr[..., 1], 8 - g_bit) # G is at index 1 in BGR
    g = np.left_shift(g, 8 - g_bit)
    b = np.right_shift(img_bgr[..., 0], 8 - b_bit) # B is at index 0 in BGR
    b = np.left_shift(b, 8 - b_bit)
    return np.dstack((b, g, r)).astype(np.uint8)

def _remove_color_ref(image_rgba):
    """
    Remove contiguous areas of the top-left pixel's color, making them transparent.
    Expects an RGBA image. Returns an RGBA image.
    """
    if image_rgba.shape[0] == 0 or image_rgba.shape[1] == 0:
        return image_rgba # Cannot process empty image

    top_left_color = image_rgba[0, 0, :3] # Compare only RGB part
    mask = np.all(image_rgba[:, :, :3] == top_left_color, axis=-1)
    
    labeled, num_labels = label(mask)
    if num_labels == 0: # No regions match the color, or empty mask
        return image_rgba

    background_label = labeled[0, 0]
    if background_label == 0: # Top-left pixel was not part of any labeled region (e.g., if mask was all False)
        return image_rgba
        
    component_mask = (labeled == background_label)
    
    output_image_rgba = image_rgba.copy()
    output_image_rgba[component_mask, 3] = 0 # Set alpha to 0
    return output_image_rgba

def _get_pixels_with_many_transparent_neighbors_ref(image_rgba, neighbor_threshold=2):
    """Identifies pixels having a certain number of transparent neighbors."""
    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.uint8)
    transparent_mask = (image_rgba[..., 3] == 0).astype(np.uint8)
    transparent_neighbor_counts = convolve(transparent_mask, kernel, mode='constant', cval=0)
    return transparent_neighbor_counts >= neighbor_threshold

def _remove_fragments_ref(image_rgba_input):
    """Make pixels transparent if they have many transparent neighbors."""
    image_rgba = image_rgba_input.copy() # Work on a copy
    # This threshold matches the implicit logic in reference.py's is_border_pixel when used by remove_fragments
    pixels_to_make_transparent_mask = _get_pixels_with_many_transparent_neighbors_ref(image_rgba, neighbor_threshold=2)
    
    image_rgba[pixels_to_make_transparent_mask, 3] = 0 # Set alpha to 0 directly
    # We don't need to set RGB to 0,0,0 if alpha is 0 for PNG.
    # To exactly match reference.py behavior of setting to (0,0,0,0):
    image_rgba[pixels_to_make_transparent_mask, :3] = 0 
    return image_rgba

def _remove_small_contiguous_areas_ref(image_rgba_input, min_size=1, max_size=10000):
    """Remove small contiguous non-transparent regions in an RGBA image."""
    image_rgba = image_rgba_input.copy() # Work on a copy
    non_transparent_mask = image_rgba[..., 3] > 0
    
    if not np.any(non_transparent_mask): # If image is fully transparent
        return image_rgba

    labeled, num_labels = label(non_transparent_mask)
    if num_labels == 0: # No non-transparent areas
        return image_rgba
        
    slices = find_objects(labeled)
    
    for i, slice_ in enumerate(slices):
        if slice_ is None:
            continue
        
        # Extract the current region from the labeled image
        region_in_slice = labeled[slice_]
        # Create a mask for the specific region (i+1) within this slice
        current_region_mask_in_slice = (region_in_slice == i + 1)
        region_size = np.sum(current_region_mask_in_slice)
        
        if min_size <= region_size <= max_size:
            # Apply the transparency to the corresponding part of the image_rgba
            # Ensure we are modifying the correct slice of image_rgba
            image_rgba_slice = image_rgba[slice_]
            # Set alpha to 0 for the pixels in this region within the slice
            image_rgba_slice[current_region_mask_in_slice, 3] = 0
            # To exactly match reference.py behavior of setting to (0,0,0,0):
            image_rgba_slice[current_region_mask_in_slice, :3] = 0
            image_rgba[slice_] = image_rgba_slice # Put the modified slice back
            
    return image_rgba

def optimize_for_print(
    img_bytes,
    do_reduce_colors: bool = True,
    r_bit: int = 4, g_bit: int = 4, b_bit: int = 4,
    do_remove_background: bool = True,
    do_remove_fragments: bool = True,
    fragment_iterations: int = 4,
    do_remove_small_areas: bool = True,
    min_area_size: int = 1, max_area_size: int = 10000
):
    """
    Optimize an image for print by reducing colors and preparing it for printing.
    
    Parameters:
    - img_bytes: Raw image bytes
    - color_depth: Number of bits per channel (1-8), lower means fewer colors
    
    Returns:
    - Tuple of (result_bytes, error_string)
    """
    try:
        # Read image from bytes
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img_cv is None:
            return None, "Failed to decode the image."
        
        # Determine if original image has alpha to decide final output format if no transparency ops are done
        original_has_alpha = img_cv.shape[2] == 4
        processed_img = img_cv.copy()

        if do_reduce_colors:
            if processed_img.shape[2] == 3: # BGR
                processed_img = _reduce_colors_ref(processed_img, r_bit, g_bit, b_bit)
            else: # BGRA
                alpha_channel = processed_img[..., 3].copy() # Preserve alpha
                bgr_component = cv2.cvtColor(processed_img, cv2.COLOR_BGRA2BGR)
                reduced_bgr = _reduce_colors_ref(bgr_component, r_bit, g_bit, b_bit)
                processed_img = cv2.cvtColor(reduced_bgr, cv2.COLOR_BGR2BGRA)
                processed_img[..., 3] = alpha_channel
        
        img_rgba_for_ops = None
        any_transparency_op_done = False

        if do_remove_background or do_remove_fragments or do_remove_small_areas:
            any_transparency_op_done = True
            if processed_img.shape[2] == 3: # Current is BGR (possibly color-reduced)
                img_rgba_for_ops = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGBA)
            else: # Current is BGRA (possibly color-reduced)
                img_rgba_for_ops = cv2.cvtColor(processed_img, cv2.COLOR_BGRA2RGBA)
            
            # Operations are performed on img_rgba_for_ops
            if do_remove_background:
                img_rgba_for_ops = _remove_color_ref(img_rgba_for_ops)
            
            if do_remove_fragments:
                for _ in range(fragment_iterations):
                    img_rgba_for_ops = _remove_fragments_ref(img_rgba_for_ops)
            
            if do_remove_small_areas:
                img_rgba_for_ops = _remove_small_contiguous_areas_ref(
                    img_rgba_for_ops, 
                    min_size=min_area_size, 
                    max_size=max_area_size
                )
            processed_img = img_rgba_for_ops # Now processed_img is RGBA
        
        # Encode to PNG
        # cv2.imencode expects BGR or BGRA
        final_img_for_encode = None
        if any_transparency_op_done: # processed_img is RGBA
            final_img_for_encode = cv2.cvtColor(processed_img, cv2.COLOR_RGBA2BGRA)
        else: # processed_img is BGR or BGRA (original format or after color reduction only)
            final_img_for_encode = processed_img # Already BGR or BGRA

        is_success, buffer = cv2.imencode('.png', final_img_for_encode)
        if not is_success:
            return None, "Failed to encode the image to PNG."
        
        return buffer.tobytes(), None
        
    except Exception as e:
        # It's helpful to log the exception server-side or return a more detailed error
        # For now, just returning the string representation
        import traceback
        # print(f"Error in optimize_for_print: {e}\n{traceback.format_exc()}")
        return None, f"Error during image processing: {str(e)}"

def reduce_colors(img, r_bit, g_bit, b_bit):
    """Reduce the number of colors in the image using bit manipulation."""
    # Process R channel (at index 0 of RGB image)
    r_channel_processed = np.right_shift(img[..., 0], 8 - r_bit)
    r_channel_processed = np.left_shift(r_channel_processed, 8 - r_bit)
    # Process G channel (at index 1 of RGB image)
    g_channel_processed = np.right_shift(img[..., 1], 8 - g_bit)
    g_channel_processed = np.left_shift(g_channel_processed, 8 - g_bit)
    # Process B channel (at index 2 of RGB image)
    b_channel_processed = np.right_shift(img[..., 2], 8 - b_bit)
    b_channel_processed = np.left_shift(b_channel_processed, 8 - b_bit)
    # Stack them in R, G, B order for correct RGB output
    return np.dstack((r_channel_processed, g_channel_processed, b_channel_processed)) 