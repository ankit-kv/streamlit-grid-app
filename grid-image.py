import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
from streamlit_sortables import sort_items
import hashlib
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.utils import ImageReader

st.title("🧱 Custom Image Grid Maker")

# Upload section
uploaded_files = st.file_uploader("Upload Images", accept_multiple_files=True, type=["png", "jpg", "jpeg", "JPG", "bmp", "gif", "webp"])
if not uploaded_files:
    st.stop()

# Fix for duplicate filenames - create unique identifiers
def create_unique_id(file_obj, index):
    """Create a unique identifier for each file using hash of content + index"""
    file_obj.seek(0)  # Reset file pointer
    content = file_obj.read()
    file_obj.seek(0)  # Reset again for later use
    
    # Create hash of first 1024 bytes for uniqueness
    content_hash = hashlib.md5(content[:1024]).hexdigest()[:8]
    base_name = os.path.splitext(file_obj.name)[0]
    extension = os.path.splitext(file_obj.name)[1]
    
    return f"{base_name}_{content_hash}{extension}", file_obj

# Create unique file mapping
unique_files = []
file_id_to_file = {}
display_names = []

for i, file_obj in enumerate(uploaded_files):
    unique_id, file_ref = create_unique_id(file_obj, i)
    unique_files.append(unique_id)
    file_id_to_file[unique_id] = file_ref
    
    # Create display name (show original name + hash if duplicate exists)
    original_names = [f.name for f in uploaded_files]
    if original_names.count(file_obj.name) > 1:
        display_names.append(f"{file_obj.name} ({unique_id.split('_')[-1].split('.')[0]})")
    else:
        display_names.append(file_obj.name)

# Grid setup with better defaults and validation
st.markdown("### 📐 Grid Configuration")
col1, col2 = st.columns(2)
with col1:
    cols = st.number_input("Number of Columns", min_value=1, max_value=20, value=min(3, len(uploaded_files)))
with col2:
    rows = st.number_input("Number of Rows", min_value=1, max_value=20, value=max(1, len(uploaded_files) // cols + (1 if len(uploaded_files) % cols else 0)))

# Auto-suggest grid dimensions
suggested_cols = int(len(uploaded_files) ** 0.5)
suggested_rows = len(uploaded_files) // suggested_cols + (1 if len(uploaded_files) % suggested_cols else 0)
if st.button(f"📏 Auto-suggest: {suggested_cols}×{suggested_rows} grid"):
    st.session_state.update({"cols": suggested_cols, "rows": suggested_rows})
    st.rerun()

st.markdown("### 🎨 Image Sizing")
col3, col4, col5 = st.columns(3)
with col3:
    resize_width = st.number_input("Width (px)", min_value=10, max_value=1000, value=256)
with col4:
    resize_height = st.number_input("Height (px)", min_value=10, max_value=1000, value=256)
with col5:
    spacing = st.number_input("Spacing (px)", min_value=0, max_value=100, value=st.session_state.get('spacing', 2), key="spacing_input")

# Maintain aspect ratio option
maintain_aspect = st.checkbox("🔒 Maintain aspect ratio", value=False, help="Keep original proportions when resizing")

# NEW: Background and transparency options
st.markdown("### 🎨 Background & Transparency")
col_bg1, col_bg2, col_bg3 = st.columns(3)
with col_bg1:
    background_type = st.selectbox(
        "Background Type",
        ["Solid Color", "Transparent", "Gradient"],
        index=0 if 'background_type' not in st.session_state else ["Solid Color", "Transparent", "Gradient"].index(st.session_state.get('background_type', 'Solid Color')),
        help="Choose background style for your grid",
        key="background_type_select"
    )
with col_bg2:
    if background_type == "Solid Color":
        bg_color = st.color_picker("Background Color", value=st.session_state.get('bg_color', '#FFFFFF'), help="Grid background color", key="bg_color_picker")
    elif background_type == "Gradient":
        bg_color1 = st.color_picker("Gradient Start", value=st.session_state.get('bg_color1', '#FFFFFF'), key="bg_color1_picker")
        bg_color2 = st.color_picker("Gradient End", value=st.session_state.get('bg_color2', '#F0F0F0'), key="bg_color2_picker")
with col_bg3:
    preserve_transparency = st.checkbox("🔍 Preserve image transparency", value=st.session_state.get('preserve_transparency', True), help="Keep transparent areas in uploaded images", key="preserve_transparency_check")

# NEW: Border options
st.markdown("### 🖼️ Image Borders")
col_border1, col_border2, col_border3, col_border4 = st.columns(4)
with col_border1:
    add_borders = st.checkbox("Add image borders", value=st.session_state.get('add_borders', False), key="add_borders_check")
with col_border2:
    if add_borders:
        border_width = st.number_input("Border width (px)", min_value=1, max_value=20, value=st.session_state.get('border_width', 2), key="border_width_input")
with col_border3:
    if add_borders:
        border_color = st.color_picker("Border color", value=st.session_state.get('border_color', '#000000'), help="Color for image borders", key="border_color_picker")
with col_border4:
    if add_borders:
        border_style = st.selectbox("Border style", ["Solid", "Dashed", "Rounded"], index=0, key="border_style_select")

# Font configuration with better error handling
st.markdown("### 🔤 Font Settings")
font_file = st.file_uploader("Optional: Upload a .ttf Font File", type=["ttf"], help="Upload a custom font for labels")

col6, col7, col8 = st.columns(3)
with col6:
    col_font_size = st.slider("Column Label Font Size", min_value=8, max_value=64, value=16)
with col7:
    row_font_size = st.slider("Row Label Font Size", min_value=8, max_value=64, value=16)
with col8:
    # NEW: Text color option
    text_color = st.color_picker("Text Color", value=st.session_state.get('text_color', '#000000'), help="Color for all text labels", key="text_color_picker")

# Load fonts with better fallback
def load_font(font_file, size):
    """Load font with proper fallback handling"""
    try:
        if font_file is not None:
            font_bytes = font_file.read()
            font_file.seek(0)  # Reset file pointer
            return ImageFont.truetype(io.BytesIO(font_bytes), size)
        else:
            # Try common system fonts
            for font_name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "calibri.ttf"]:
                try:
                    return ImageFont.truetype(font_name, size)
                except:
                    continue
            # Final fallback
            return ImageFont.load_default()
    except Exception as e:
        st.warning(f"⚠️ Font loading issue: {str(e)}. Using default font.")
        return ImageFont.load_default()

font_col = load_font(font_file, col_font_size)
font_row = load_font(font_file, row_font_size)

st.markdown("### 🌀 Last Row Centering")
center_last_row = st.checkbox("🌀 Center last row if incomplete", value=False)

# Label configuration
st.markdown("### 🏷️ Labels")
col8, col9 = st.columns(2)
with col8:
    show_col_labels = st.checkbox("Show Column Labels", value=True)
with col9:  
    show_row_labels = st.checkbox("Show Row Labels", value=False)

# Advanced label positioning options
if show_col_labels or show_row_labels:
    st.markdown("#### 🎯 Label Positioning Options")
    
    # Column label options
    if show_col_labels:
        st.markdown("**Column Labels:**")
        col_label_pos = st.selectbox(
            "Column Label Position",
            ["Top", "Bottom", "Both (Top & Bottom)"],
            index=0,
            help="Where to place column labels relative to the grid"
        )
    else:
        col_label_pos = "Top"
    
    # Row label options  
    if show_row_labels:
        st.markdown("**Row Labels:**")
        col_row1, col_row2 = st.columns(2)
        with col_row1:
            row_label_pos = st.selectbox(
                "Row Label Position", 
                ["Left", "Right", "Both (Left & Right)"],
                index=0,
                help="Where to place row labels relative to the grid"
            )
        with col_row2:
            row_label_orientation = st.selectbox(
                "Row Label Orientation",
                ["Horizontal", "Vertical"],
                index=0,
                help="Text direction for row labels"
            )
    else:
        row_label_pos = "Left"
        row_label_orientation = "Horizontal"

# Dynamic label inputs
if show_col_labels:
    st.markdown("#### Column Labels")
    col_labels = []
    for i in range(int(cols)):
        col_labels.append(st.text_input(f"Column {i+1}", value=f"Col {i+1}", key=f"col_label_{i}"))
else:
    col_labels = [""] * int(cols)

if show_row_labels:
    st.markdown("#### Row Labels")
    row_labels = []
    for i in range(int(rows)):
        row_labels.append(st.text_input(f"Row {i+1}", value=f"Row {i+1}", key=f"row_label_{i}"))
else:
    row_labels = [""] * int(rows)

expected_count = int(rows * cols)
available_count = len(uploaded_files)

if available_count < expected_count:
    st.warning(f"⚠️ Fewer images ({available_count}) than grid size ({rows}×{cols} = {expected_count}). Last row will be partially filled.")
    final_count = available_count
else:
    if available_count > expected_count:
        st.info(f"ℹ️ Using only the first {expected_count} images from {available_count} uploaded.")
    final_count = expected_count

# Update display_names and unique_files to use only required number
display_names = display_names[:final_count]
unique_files = unique_files[:final_count]

# Calculate label flags early (needed for preview)
has_col_labels = show_col_labels and any(label.strip() for label in col_labels)
has_row_labels = show_row_labels and any(label.strip() for label in row_labels)

# Enhanced Image Arrangement System
st.markdown("### 🔃 Arrange Images")

# Create thumbnail previews for better visualization
def create_thumbnail(file_obj, size=(80, 80)):
    """Create small thumbnail for preview"""
    try:
        img = Image.open(file_obj).convert("RGBA" if preserve_transparency else "RGB")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        # Create square thumbnail with white background
        thumb = Image.new("RGBA" if preserve_transparency else "RGB", size, (255, 255, 255, 255) if preserve_transparency else (255, 255, 255))
        offset = ((size[0] - img.size[0]) // 2, (size[1] - img.size[1]) // 2)
        thumb.paste(img, offset)
        return thumb
    except:
        # Create placeholder if image fails to load
        thumb = Image.new("RGB", size, (240, 240, 240))
        return thumb

# Arrangement method selection
arrangement_method = st.radio(
    "Choose arrangement method:",
    ["🎯 Simple List (drag names)", "🔢 Manual Position Input"],
    index=0
)

if arrangement_method == "🎯 Simple List (drag names)":
    # Original method - drag and drop names
    st.info("💡 Drag and drop to reorder images in the grid")
    sorted_display_names = sort_items(display_names, direction="vertical")
    
    if not sorted_display_names or len(sorted_display_names) != min(expected_count, len(uploaded_files)):
        st.warning("⚠️ Please arrange all images")
        st.stop()
    
    display_to_unique = {display_names[i]: unique_files[i] for i in range(len(display_names))}
    sorted_unique_ids = [display_to_unique[name] for name in sorted_display_names]

else:  # Manual Position Input
    st.info("🔢 Enter the position number (1 to N) for each image")
    
    # Create manual position inputs
    position_inputs = {}
    cols_manual = st.columns(3)
    
    for idx in range(min(expected_count, len(uploaded_files))):
        col_idx = idx % 3
        with cols_manual[col_idx]:
            thumb = create_thumbnail(file_id_to_file[unique_files[idx]], (60, 60))
            st.image(thumb)
            position_inputs[idx] = st.number_input(
                f"Position for {display_names[idx][:20]}...",
                min_value=1,
                max_value=expected_count,
                value=idx + 1,
                key=f"manual_pos_{idx}"
            )
    
    # Validate positions
    positions = list(position_inputs.values())
    if len(set(positions)) != len(positions):
        st.error("❌ Each position must be unique! Please check for duplicates.")
        st.stop()
    
    if set(positions) != set(range(1, expected_count + 1)):
        st.error(f"❌ Please use positions 1 to {expected_count} exactly once.")
        st.stop()
    
    # Create sorted list based on manual positions
    position_to_idx = {pos: idx for idx, pos in position_inputs.items()}
    sorted_unique_ids = []
    for pos in range(1, expected_count + 1):
        img_idx = position_to_idx[pos]
        sorted_unique_ids.append(unique_files[img_idx])
    
    st.success("✅ All positions assigned correctly!")

# Process images with better resizing and border support
def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def resize_image(img, width, height, maintain_aspect, add_border=False, border_width=0, border_color="#000000"):
    """Resize image with optional aspect ratio preservation and borders"""
    # Convert to RGBA if preserving transparency, otherwise RGB
    if preserve_transparency and img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGBA')
    else:
        img = img.convert('RGB')
    
    if maintain_aspect:
        img.thumbnail((width, height), Image.Resampling.LANCZOS)
        # Create background
        if preserve_transparency and img.mode == 'RGBA':
            bg = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        else:
            bg = Image.new("RGB", (width, height), (255, 255, 255))
        offset = ((width - img.size[0]) // 2, (height - img.size[1]) // 2)
        if preserve_transparency and img.mode == 'RGBA':
            bg.paste(img, offset, img)
        else:
            bg.paste(img, offset)
        img = bg
    else:
        img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # Add border if requested
    if add_border and border_width > 0:
        border_rgb = hex_to_rgb(border_color)
        if border_style == "Solid":
            # Create bordered image
            bordered_width = width + 2 * border_width
            bordered_height = height + 2 * border_width
            if preserve_transparency and img.mode == 'RGBA':
                bordered_img = Image.new("RGBA", (bordered_width, bordered_height), border_rgb + (255,))
                bordered_img.paste(img, (border_width, border_width), img)
            else:
                bordered_img = Image.new("RGB", (bordered_width, bordered_height), border_rgb)
                bordered_img.paste(img, (border_width, border_width))
            return bordered_img
        elif border_style == "Rounded":
            # Create rounded border (simplified version)
            bordered_width = width + 2 * border_width
            bordered_height = height + 2 * border_width
            if preserve_transparency and img.mode == 'RGBA':
                bordered_img = Image.new("RGBA", (bordered_width, bordered_height), border_rgb + (255,))
                bordered_img.paste(img, (border_width, border_width), img)
            else:
                bordered_img = Image.new("RGB", (bordered_width, bordered_height), border_rgb)
                bordered_img.paste(img, (border_width, border_width))
            return bordered_img
    
    return img

def create_rotated_text(text, font, angle=90, text_color="#000000"):
    """Create rotated text image for vertical labels"""
    # Get text dimensions
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create image with text
    text_img = Image.new("RGBA", (text_width + 10, text_height + 10), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_img)
    text_rgb = hex_to_rgb(text_color)
    text_draw.text((5, 5), text, fill=text_rgb + (255,), font=font)
    
    # Rotate the text image
    if angle != 0:
        text_img = text_img.rotate(angle, expand=True)
    
    return text_img

def create_gradient_background(width, height, color1, color2, direction="vertical"):
    """Create a gradient background"""
    gradient = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(gradient)
    
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    
    if direction == "vertical":
        for y in range(height):
            ratio = y / height
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    else:  # horizontal
        for x in range(width):
            ratio = x / width
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))
    
    return gradient

try:
    images = []
    for unique_id in sorted_unique_ids:
        img = Image.open(file_id_to_file[unique_id])
        # Calculate actual dimensions including border
        actual_width = resize_width + (2 * border_width if add_borders else 0)
        actual_height = resize_height + (2 * border_width if add_borders else 0)
        resized_img = resize_image(img, resize_width, resize_height, maintain_aspect, add_borders, border_width if add_borders else 0, border_color if add_borders else "#000000")
        images.append(resized_img)
except Exception as e:
    st.error(f"❌ Error processing images: {str(e)}")
    st.stop()

# Show arrangement summary
with st.expander("📋 Current Arrangement Summary"):
    for idx, unique_id in enumerate(sorted_unique_ids):
        row_pos, col_pos = divmod(idx, int(cols))
        original_name = file_id_to_file[unique_id].name
        st.text(f"Position {idx+1} (Row {row_pos+1}, Col {col_pos+1}): {original_name}")

# Generate grid with enhanced background and transparency support
draw_temp = ImageDraw.Draw(Image.new("RGB", (100, 100)))

# Calculate actual image dimensions (including borders)
actual_img_width = resize_width + (2 * border_width if add_borders else 0)
actual_img_height = resize_height + (2 * border_width if add_borders else 0)

# Calculate label dimensions based on positioning options
top_label_height = 0
bottom_label_height = 0
left_label_width = 0
right_label_width = 0

if has_col_labels:
    max_height = 0
    for label in col_labels:
        if label.strip():
            bbox = draw_temp.textbbox((0, 0), label, font=font_col)
            max_height = max(max_height, bbox[3] - bbox[1])
    
    label_height = max_height + 15
    if col_label_pos == "Top":
        top_label_height = label_height
    elif col_label_pos == "Bottom":
        bottom_label_height = label_height
    elif col_label_pos == "Both (Top & Bottom)":
        top_label_height = label_height
        bottom_label_height = label_height

if has_row_labels:
    if row_label_orientation == "Horizontal":
        max_width = 0
        for label in row_labels:
            if label.strip():
                bbox = draw_temp.textbbox((0, 0), label, font=font_row)
                max_width = max(max_width, bbox[2] - bbox[0])
        label_width = max_width + 15
    else:
        max_height = 0
        for label in row_labels:
            if label.strip():
                bbox = draw_temp.textbbox((0, 0), label, font=font_row)
                max_height = max(max_height, bbox[3] - bbox[1])
        label_width = max_height + 15
    
    if row_label_pos == "Left":
        left_label_width = label_width
    elif row_label_pos == "Right":
        right_label_width = label_width
    elif row_label_pos == "Both (Left & Right)":
        left_label_width = label_width
        right_label_width = label_width

# Calculate final dimensions
grid_width = int(left_label_width + cols * actual_img_width + (cols - 1) * spacing + right_label_width)
grid_height = int(top_label_height + rows * actual_img_height + (rows - 1) * spacing + bottom_label_height)

# Create grid with appropriate background
if background_type == "Transparent":
    grid_img = Image.new("RGBA", (grid_width, grid_height), (255, 255, 255, 0))
elif background_type == "Gradient":
    grid_img = create_gradient_background(grid_width, grid_height, bg_color1, bg_color2)
else:  # Solid Color
    bg_rgb = hex_to_rgb(bg_color)
    grid_img = Image.new("RGB", (grid_width, grid_height), bg_rgb)

draw = ImageDraw.Draw(grid_img)
text_rgb = hex_to_rgb(text_color)

# Draw column labels with positioning options
if has_col_labels:
    for i, label in enumerate(col_labels):
        if label.strip():
            bbox = draw.textbbox((0, 0), label, font=font_col)
            text_w = bbox[2] - bbox[0]
            x = int(left_label_width + i * (actual_img_width + spacing) + (actual_img_width - text_w) / 2)
            
            # Top labels
            if col_label_pos in ["Top", "Both (Top & Bottom)"]:
                y = 5
                draw.text((x, y), label, fill=text_rgb, font=font_col)
            
            # Bottom labels
            if col_label_pos in ["Bottom", "Both (Top & Bottom)"]:
                y = int(grid_height - bottom_label_height + 5)
                draw.text((x, y), label, fill=text_rgb, font=font_col)

# Draw row labels with positioning and orientation options
if has_row_labels:
    for i, label in enumerate(row_labels):
        if label.strip():
            if row_label_orientation == "Horizontal":
                bbox = draw.textbbox((0, 0), label, font=font_row)
                text_h = bbox[3] - bbox[1]
                y = int(top_label_height + i * (actual_img_height + spacing) + (actual_img_height - text_h) / 2)
                
                # Left labels
                if row_label_pos in ["Left", "Both (Left & Right)"]:
                    x = 5
                    draw.text((x, y), label, fill=text_rgb, font=font_row)
                
                # Right labels
                if row_label_pos in ["Right", "Both (Left & Right)"]:
                    x = int(grid_width - right_label_width + 5)
                    draw.text((x, y), label, fill=text_rgb, font=font_row)
            
            else:
                # Vertical text (rotated)
                rotated_text = create_rotated_text(label, font_row, 90, text_color)
                y_center = int(top_label_height + i * (actual_img_height + spacing) + actual_img_height / 2)
                y = int(y_center - rotated_text.size[1] / 2)
                
                # Left labels
                if row_label_pos in ["Left", "Both (Left & Right)"]:
                    x_center = int(left_label_width / 2)
                    x = int(x_center - rotated_text.size[0] / 2)
                    if background_type == "Transparent":
                        grid_img.paste(rotated_text, (x, y), rotated_text)
                    else:
                        temp_bg = Image.new("RGB", rotated_text.size, hex_to_rgb(bg_color) if background_type == "Solid Color" else (255, 255, 255))
                        temp_bg.paste(rotated_text, (0, 0), rotated_text)
                        grid_img.paste(temp_bg, (x, y))
                
                # Right labels
                if row_label_pos in ["Right", "Both (Left & Right)"]:
                    x_center = int(grid_width - right_label_width / 2)
                    x = int(x_center - rotated_text.size[0] / 2)
                    if background_type == "Transparent":
                        grid_img.paste(rotated_text, (x, y), rotated_text)
                    else:
                        temp_bg = Image.new("RGB", rotated_text.size, hex_to_rgb(bg_color) if background_type == "Solid Color" else (255, 255, 255))
                        temp_bg.paste(rotated_text, (0, 0), rotated_text)
                        grid_img.paste(temp_bg, (x, y))

# Paste images into grid
for idx, img in enumerate(images):
    row_idx, col_idx = divmod(idx, int(cols))

    # Check if it's the last row and if it has fewer images
    if center_last_row and row_idx == rows - 1:
        remaining_images = len(images) - row_idx * cols
        if remaining_images < cols:
            total_img_width = remaining_images * actual_img_width + (remaining_images - 1) * spacing
            start_x = int(left_label_width + (cols * (actual_img_width + spacing) - spacing - total_img_width) / 2)
            x = int(start_x + col_idx * (actual_img_width + spacing))
        else:
            x = int(left_label_width + col_idx * (actual_img_width + spacing))
    else:
        x = int(left_label_width + col_idx * (actual_img_width + spacing))
    
    y = int(top_label_height + row_idx * (actual_img_height + spacing))
    
    # Paste image with transparency support
    if preserve_transparency and img.mode == 'RGBA' and background_type == "Transparent":
        grid_img.paste(img, (x, y), img)
    elif preserve_transparency and img.mode == 'RGBA':
        grid_img.paste(img, (x, y), img)
    else:
        grid_img.paste(img, (x, y))

# Display results
st.markdown("### 🎯 Generated Grid")
st.image(grid_img, caption="Your Enhanced Custom Image Grid")

# Enhanced download options
st.markdown("### 📥 Download Options")

# NEW: PDF generation function
def create_pdf_with_grid(grid_img, filename="image_grid.pdf", page_size="A4"):
    """Create PDF with the grid image"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4, landscape
    from reportlab.lib.utils import ImageReader
    import io
    
    # Convert PIL image to format that reportlab can use
    img_buffer = io.BytesIO()
    if grid_img.mode == 'RGBA':
        # Convert RGBA to RGB for PDF
        rgb_img = Image.new('RGB', grid_img.size, (255, 255, 255))
        rgb_img.paste(grid_img, mask=grid_img.split()[-1])
        rgb_img.save(img_buffer, format='PNG')
    else:
        grid_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # Create PDF
    pdf_buffer = io.BytesIO()
    
    # Set page size
    if page_size == "A4":
        page_width, page_height = A4
    elif page_size == "A4 Landscape":
        page_width, page_height = landscape(A4)
    else:  # Letter
        page_width, page_height = letter
    
    c = canvas.Canvas(pdf_buffer, pagesize=(page_width, page_height))
    
    # Calculate scaling to fit image on page with margins
    margin = 50
    available_width = page_width - 2 * margin
    available_height = page_height - 2 * margin
    
    img_width, img_height = grid_img.size
    scale_x = available_width / img_width
    scale_y = available_height / img_height
    scale = min(scale_x, scale_y, 1.0)  # Don't scale up
    
    # Calculate centered position
    scaled_width = img_width * scale
    scaled_height = img_height * scale
    x = (page_width - scaled_width) / 2
    y = (page_height - scaled_height) / 2
    
    # Draw image
    c.drawImage(ImageReader(img_buffer), x, y, scaled_width, scaled_height)
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

col10, col11, col12, col13 = st.columns(4)

with col10:
    # PNG download (default)
    buf_png = io.BytesIO()
    if background_type == "Transparent":
        grid_img.save(buf_png, format="PNG", optimize=True)
    else:
        grid_img.save(buf_png, format="PNG", optimize=True)
    st.download_button(
        "📥 Download PNG", 
        buf_png.getvalue(), 
        file_name="image_grid.png", 
        mime="image/png"
    )

with col11:
    # JPEG download (convert RGBA to RGB for JPEG)
    buf_jpg = io.BytesIO()
    if grid_img.mode == 'RGBA':
        # Convert RGBA to RGB with white background for JPEG
        rgb_img = Image.new('RGB', grid_img.size, (255, 255, 255))
        rgb_img.paste(grid_img, mask=grid_img.split()[-1])
        rgb_img.save(buf_jpg, format="JPEG", quality=95, optimize=True)
    else:
        grid_img.save(buf_jpg, format="JPEG", quality=95, optimize=True)
    st.download_button(
        "📥 Download JPEG", 
        buf_jpg.getvalue(), 
        file_name="image_grid.jpg", 
        mime="image/jpeg"
    )

with col12:
    # High quality PNG
    buf_hq = io.BytesIO()
    grid_img.save(buf_hq, format="PNG", compress_level=1)
    st.download_button(
        "📥 Download HQ PNG", 
        buf_hq.getvalue(), 
        file_name="image_grid_hq.png", 
        mime="image/png"
    )

with col13:
    # NEW: PDF download options
    pdf_page_size = st.selectbox(
        "PDF Page Size",
        ["A4", "A4 Landscape", "Letter"],
        index=0,
        key="pdf_page_size"
    )

# PDF download button (separate row for better layout)
col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 1, 2])
with col_pdf1:
    if st.button("📄 Generate PDF"):
        with st.spinner("Creating PDF..."):
            try:
                pdf_data = create_pdf_with_grid(grid_img, page_size=pdf_page_size)
                st.session_state['pdf_data'] = pdf_data
                st.success("PDF generated successfully!")
            except Exception as e:
                st.error(f"Error creating PDF: {str(e)}")

with col_pdf2:
    if 'pdf_data' in st.session_state:
        st.download_button(
            "📥 Download PDF",
            st.session_state['pdf_data'],
            file_name="image_grid.pdf",
            mime="application/pdf"
        )

with col_pdf3:
    st.info("💡 PDF will automatically scale your grid to fit the page")

# Additional format options
st.markdown("#### 🎨 Additional Formats")
col_extra1, col_extra2, col_extra3 = st.columns(3)

with col_extra1:
    # WebP format
    buf_webp = io.BytesIO()
    if grid_img.mode == 'RGBA':
        grid_img.save(buf_webp, format="WebP", quality=90, method=6)
    else:
        grid_img.save(buf_webp, format="WebP", quality=90, method=6)
    st.download_button(
        "📥 Download WebP", 
        buf_webp.getvalue(), 
        file_name="image_grid.webp", 
        mime="image/webp"
    )

with col_extra2:
    # TIFF format
    buf_tiff = io.BytesIO()
    if grid_img.mode == 'RGBA':
        grid_img.save(buf_tiff, format="TIFF", compression="lzw")
    else:
        grid_img.save(buf_tiff, format="TIFF", compression="lzw")
    st.download_button(
        "📥 Download TIFF", 
        buf_tiff.getvalue(), 
        file_name="image_grid.tiff", 
        mime="image/tiff"
    )

with col_extra3:
    # BMP format
    buf_bmp = io.BytesIO()
    if grid_img.mode == 'RGBA':
        # Convert RGBA to RGB for BMP
        rgb_img = Image.new('RGB', grid_img.size, (255, 255, 255))
        rgb_img.paste(grid_img, mask=grid_img.split()[-1])
        rgb_img.save(buf_bmp, format="BMP")
    else:
        grid_img.save(buf_bmp, format="BMP")
    st.download_button(
        "📥 Download BMP", 
        buf_bmp.getvalue(), 
        file_name="image_grid.bmp", 
        mime="image/bmp"
    )

# Show enhanced grid info
st.markdown("### 📊 Grid Information")
info_text = f"""
**Grid Size:** {rows}×{cols} = {len(images)} images  
**Image Dimensions:** {resize_width}×{resize_height} px  
**Actual Image Size:** {actual_img_width}×{actual_img_height} px (with borders)  
**Final Grid Size:** {grid_width}×{grid_height} px  
**Spacing:** {spacing}px  
**Background:** {background_type}  
**Transparency Preserved:** {'Yes' if preserve_transparency else 'No'}  
**Borders:** {'Yes' if add_borders else 'No'} {f'({border_width}px, {border_color})' if add_borders else ''}  
**Text Color:** {text_color}  
**File Size (PNG):** ~{len(buf_png.getvalue()) / 1024:.1f} KB
"""
st.info(info_text)

# NEW: Grid statistics and analysis
with st.expander("📈 Advanced Grid Analysis"):
    st.markdown("#### Image Format Distribution")
    format_counts = {}
    for unique_id in sorted_unique_ids:
        file_obj = file_id_to_file[unique_id]
        try:
            with Image.open(file_obj) as img:
                format_name = img.format or "Unknown"
                format_counts[format_name] = format_counts.get(format_name, 0) + 1
        except:
            format_counts["Error"] = format_counts.get("Error", 0) + 1
    
    for fmt, count in format_counts.items():
        st.text(f"{fmt}: {count} images ({count/len(sorted_unique_ids)*100:.1f}%)")
    
    st.markdown("#### Color Space Information")
    color_modes = {}
    total_pixels = 0
    for unique_id in sorted_unique_ids:
        file_obj = file_id_to_file[unique_id]
        try:
            with Image.open(file_obj) as img:
                mode = img.mode
                color_modes[mode] = color_modes.get(mode, 0) + 1
                total_pixels += img.size[0] * img.size[1]
        except:
            color_modes["Error"] = color_modes.get("Error", 0) + 1
    
    for mode, count in color_modes.items():
        st.text(f"{mode}: {count} images ({count/len(sorted_unique_ids)*100:.1f}%)")
    
    st.text(f"Total original pixels processed: {total_pixels:,}")
    st.text(f"Final grid pixels: {grid_width * grid_height:,}")

# NEW: Quick presets for common configurations
st.markdown("### ⚡ Quick Presets")
col_preset1, col_preset2, col_preset3, col_preset4 = st.columns(4)

with col_preset1:
    if st.button("🎨 Art Gallery", help="White background, black borders, elegant labels"):
        st.session_state.update({
            'background_type': 'Solid Color',
            'bg_color': '#FFFFFF',
            'add_borders': True,
            'border_width': 3,
            'border_color': '#000000',
            'text_color': '#000000',
            'spacing': 10,
            'preserve_transparency': False
        })
        st.rerun()

with col_preset2:
    if st.button("🌙 Dark Mode", help="Dark background, light borders and text"):
        st.session_state.update({
            'background_type': 'Solid Color',
            'bg_color': '#2E2E2E',
            'add_borders': True,
            'border_width': 2,
            'border_color': '#FFFFFF',
            'text_color': '#FFFFFF',
            'spacing': 5,
            'preserve_transparency': False
        })
        st.rerun()

with col_preset3:
    if st.button("🎭 Transparent", help="Transparent background, no borders"):
        st.session_state.update({
            'background_type': 'Transparent',
            'add_borders': False,
            'text_color': '#000000',
            'spacing': 2,
            'preserve_transparency': True,
            'border_width': 2,
            'border_color': '#000000'
        })
        st.rerun()

with col_preset4:
    if st.button("🌈 Gradient", help="Gradient background with colorful borders"):
        st.session_state.update({
            'background_type': 'Gradient',
            'bg_color1': '#FFE5E5',
            'bg_color2': '#E5F3FF',
            'add_borders': True,
            'border_width': 2,
            'border_color': '#FF6B6B',
            'text_color': '#2C3E50',
            'spacing': 8,
            'preserve_transparency': False
        })
        st.rerun()

# Update variables after potential preset changes
if 'background_type' in st.session_state:
    background_type = st.session_state['background_type']
if 'bg_color' in st.session_state:
    bg_color = st.session_state['bg_color']
if 'bg_color1' in st.session_state and background_type == "Gradient":
    bg_color1 = st.session_state['bg_color1']
if 'bg_color2' in st.session_state and background_type == "Gradient":
    bg_color2 = st.session_state['bg_color2']
if 'add_borders' in st.session_state:
    add_borders = st.session_state['add_borders']
if 'border_width' in st.session_state:
    border_width = st.session_state['border_width']
if 'border_color' in st.session_state:
    border_color = st.session_state['border_color']
if 'text_color' in st.session_state:
    text_color = st.session_state['text_color']
if 'spacing' in st.session_state:
    spacing = st.session_state['spacing']
if 'preserve_transparency' in st.session_state:
    preserve_transparency = st.session_state['preserve_transparency']

st.markdown("### 💡 Tips & Tricks")
with st.expander("Click to see helpful tips"):
    st.markdown("""
    **🎨 Design Tips:**
    - Use transparent backgrounds for overlays or web graphics
    - Add borders to create a professional gallery look
    - Gradient backgrounds work great for social media posts
    - Dark mode is perfect for photography portfolios
    
    **📐 Layout Tips:**
    - Enable "Center last row" for better visual balance
    - Use vertical row labels to save horizontal space
    - Match border colors to your text color for consistency
    
    **💾 Export Tips:**
    - Use PNG for images with transparency
    - Choose JPEG for smaller file sizes (no transparency)
    - PDF is perfect for printing or professional presentations
    - WebP offers the best compression for web use
    
    **🔧 Technical Notes:**
    - Transparent images preserve their alpha channel
    - PDF exports automatically scale to fit the page
    - High-quality PNG uses less compression for better quality
    """)

st.markdown("---")
st.markdown("### 👨‍💻 Credits")
st.markdown("""
**Enhanced Custom Image Grid Maker v2.0**  
Developed by Ankit Kumar Verma  

**New Features in v2.0:**
- 🎨 Customizable background colors and gradients
- 🔍 Transparent background support
- 🖼️ Image borders with multiple styles
- 🌈 Custom text colors
- 📄 PDF export functionality
- 🎭 Advanced transparency handling
- ⚡ Quick preset configurations
- 📊 Advanced grid analysis

This tool is open-source. Find the code on [GitHub](https://github.com/your-repo)
""")

st.markdown("---")
st.markdown("*💡 Pro tip: Bookmark this page for quick access to your enhanced image grid maker!*")
