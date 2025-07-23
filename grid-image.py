import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
from streamlit_sortables import sort_items
import hashlib
import os

st.title("🧱 Custom Image Grid Maker")

# Upload section
uploaded_files = st.file_uploader("Upload Images", accept_multiple_files=True, type=["png", "jpg", "jpeg", "JPG", "bmp"])
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
    spacing = st.number_input("Spacing (px)", min_value=0, max_value=100, value=10)

# Maintain aspect ratio option
maintain_aspect = st.checkbox("🔒 Maintain aspect ratio", value=False, help="Keep original proportions when resizing")

# Font configuration with better error handling
st.markdown("### 🔤 Font Settings")
font_file = st.file_uploader("Optional: Upload a .ttf Font File", type=["ttf"], help="Upload a custom font for labels")

col6, col7 = st.columns(2)
with col6:
    col_font_size = st.slider("Column Label Font Size", min_value=8, max_value=64, value=16)
with col7:
    row_font_size = st.slider("Row Label Font Size", min_value=8, max_value=64, value=16)

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

# Image arrangement
expected_count = int(rows * cols)
if len(uploaded_files) != expected_count:
    st.warning(f"⚠️ Grid size ({rows}×{cols} = {expected_count}) doesn't match uploaded images ({len(uploaded_files)})")
    if len(uploaded_files) < expected_count:
        st.error(f"❌ Need {expected_count - len(uploaded_files)} more images")
        st.stop()
    else:
        st.info(f"ℹ️ Only first {expected_count} images will be used")

# Calculate label flags early (needed for preview)
has_col_labels = show_col_labels and any(label.strip() for label in col_labels)
has_row_labels = show_row_labels and any(label.strip() for label in row_labels)

# Enhanced Image Arrangement System
st.markdown("### 🔃 Arrange Images")

# Create thumbnail previews for better visualization
def create_thumbnail(file_obj, size=(80, 80)):
    """Create small thumbnail for preview"""
    try:
        img = Image.open(file_obj).convert("RGB")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        # Create square thumbnail with white background
        thumb = Image.new("RGB", size, (255, 255, 255))
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
    sorted_display_names = sort_items(display_names[:expected_count], direction="vertical")
    
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

# Process images with better resizing
def resize_image(img, width, height, maintain_aspect):
    """Resize image with optional aspect ratio preservation"""
    if maintain_aspect:
        img.thumbnail((width, height), Image.Resampling.LANCZOS)
        # Create white background and center the image
        bg = Image.new("RGB", (width, height), (255, 255, 255))
        offset = ((width - img.size[0]) // 2, (height - img.size[1]) // 2)
        bg.paste(img, offset)
        return bg
    else:
        return img.resize((width, height), Image.Resampling.LANCZOS)

def create_rotated_text(text, font, angle=90):
    """Create rotated text image for vertical labels"""
    # Get text dimensions
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create image with text
    text_img = Image.new("RGBA", (text_width + 10, text_height + 10), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_img)
    text_draw.text((5, 5), text, fill=(0, 0, 0, 255), font=font)
    
    # Rotate the text image
    if angle != 0:
        text_img = text_img.rotate(angle, expand=True)
    
    return text_img

try:
    images = []
    for unique_id in sorted_unique_ids:
        img = Image.open(file_id_to_file[unique_id]).convert("RGB")
        resized_img = resize_image(img, resize_width, resize_height, maintain_aspect)
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


# Generate grid with better spacing calculations
# Text space estimation (labels already calculated above)
draw_temp = ImageDraw.Draw(Image.new("RGB", (100, 100)))

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
        # For horizontal text, width is the limiting factor
        max_width = 0
        for label in row_labels:
            if label.strip():
                bbox = draw_temp.textbbox((0, 0), label, font=font_row)
                max_width = max(max_width, bbox[2] - bbox[0])
        label_width = max_width + 15
    else:
        # For vertical text, height becomes width after rotation
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
grid_width = int(left_label_width + cols * resize_width + (cols - 1) * spacing + right_label_width)
grid_height = int(top_label_height + rows * resize_height + (rows - 1) * spacing + bottom_label_height)

# Create and draw grid
grid_img = Image.new("RGB", (grid_width, grid_height), color=(255, 255, 255))
draw = ImageDraw.Draw(grid_img)

# Draw column labels with positioning options
if has_col_labels:
    for i, label in enumerate(col_labels):
        if label.strip():
            bbox = draw.textbbox((0, 0), label, font=font_col)
            text_w = bbox[2] - bbox[0]
            x = int(left_label_width + i * (resize_width + spacing) + (resize_width - text_w) / 2)
            
            # Top labels
            if col_label_pos in ["Top", "Both (Top & Bottom)"]:
                y = 5
                draw.text((x, y), label, fill=(0, 0, 0), font=font_col)
            
            # Bottom labels
            if col_label_pos in ["Bottom", "Both (Top & Bottom)"]:
                y = int(grid_height - bottom_label_height + 5)
                draw.text((x, y), label, fill=(0, 0, 0), font=font_col)

# Draw row labels with positioning and orientation options
if has_row_labels:
    for i, label in enumerate(row_labels):
        if label.strip():
            if row_label_orientation == "Horizontal":
                # Horizontal text
                bbox = draw.textbbox((0, 0), label, font=font_row)
                text_h = bbox[3] - bbox[1]
                y = int(top_label_height + i * (resize_height + spacing) + (resize_height - text_h) / 2)
                
                # Left labels
                if row_label_pos in ["Left", "Both (Left & Right)"]:
                    x = 5
                    draw.text((x, y), label, fill=(0, 0, 0), font=font_row)
                
                # Right labels
                if row_label_pos in ["Right", "Both (Left & Right)"]:
                    x = int(grid_width - right_label_width + 5)
                    draw.text((x, y), label, fill=(0, 0, 0), font=font_row)
            
            else:
                # Vertical text (rotated)
                rotated_text = create_rotated_text(label, font_row, 90)
                y_center = int(top_label_height + i * (resize_height + spacing) + resize_height / 2)
                y = int(y_center - rotated_text.size[1] / 2)
                
                # Left labels
                if row_label_pos in ["Left", "Both (Left & Right)"]:
                    x_center = int(left_label_width / 2)
                    x = int(x_center - rotated_text.size[0] / 2)
                    # Convert rotated text to RGB for pasting
                    temp_bg = Image.new("RGB", rotated_text.size, (255, 255, 255))
                    temp_bg.paste(rotated_text, (0, 0), rotated_text)
                    grid_img.paste(temp_bg, (x, y))
                
                # Right labels
                if row_label_pos in ["Right", "Both (Left & Right)"]:
                    x_center = int(grid_width - right_label_width / 2)
                    x = int(x_center - rotated_text.size[0] / 2)
                    # Convert rotated text to RGB for pasting
                    temp_bg = Image.new("RGB", rotated_text.size, (255, 255, 255))
                    temp_bg.paste(rotated_text, (0, 0), rotated_text)
                    grid_img.paste(temp_bg, (x, y))

# Paste images into grid
for idx, img in enumerate(images):
    row_idx, col_idx = divmod(idx, int(cols))
    x = int(left_label_width + col_idx * (resize_width + spacing))
    y = int(top_label_height + row_idx * (resize_height + spacing))
    grid_img.paste(img, (x, y))

# Display results
st.markdown("### 🎯 Generated Grid")
st.image(grid_img, caption="Your Custom Image Grid")

# Enhanced download options
st.markdown("### 📥 Download Options")
col10, col11, col12 = st.columns(3)

with col10:
    # PNG download (default)
    buf_png = io.BytesIO()
    grid_img.save(buf_png, format="PNG", optimize=True)
    st.download_button(
        "📥 Download PNG", 
        buf_png.getvalue(), 
        file_name="image_grid.png", 
        mime="image/png"
    )

with col11:
    # JPEG download
    buf_jpg = io.BytesIO()
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

# Show grid info
st.markdown("### 📊 Grid Information")
st.info(f"""
**Grid Size:** {rows}×{cols} = {len(images)} images  
**Image Dimensions:** {resize_width}×{resize_height} px  
**Final Grid Size:** {grid_width}×{grid_height} px  
**Spacing:** {spacing}px  
**File Size:** ~{len(buf_png.getvalue()) / 1024:.1f} KB
""")


st.markdown("### Credits")
st.markdown("This tool was developed by Ankit Kumar Verma and is open-source. You can find the source code on [GitHub]")
