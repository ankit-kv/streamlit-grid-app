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

# Image reordering with improved UX
st.markdown("### 🔃 Arrange Images")
st.info("💡 Drag and drop to reorder images in the grid")

# Use display names for better UX
sorted_display_names = sort_items(display_names[:expected_count], direction="vertical")

if not sorted_display_names or len(sorted_display_names) != min(expected_count, len(uploaded_files)):
    st.warning("⚠️ Please arrange all images")
    st.stop()

# Map back to unique IDs
display_to_unique = {display_names[i]: unique_files[i] for i in range(len(display_names))}
sorted_unique_ids = [display_to_unique[name] for name in sorted_display_names]

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

try:
    images = []
    for unique_id in sorted_unique_ids:
        img = Image.open(file_id_to_file[unique_id]).convert("RGB")
        resized_img = resize_image(img, resize_width, resize_height, maintain_aspect)
        images.append(resized_img)
except Exception as e:
    st.error(f"❌ Error processing images: {str(e)}")
    st.stop()

# Generate grid with better spacing calculations
has_col_labels = show_col_labels and any(label.strip() for label in col_labels)
has_row_labels = show_row_labels and any(label.strip() for label in row_labels)

# Calculate label dimensions more accurately
draw_temp = ImageDraw.Draw(Image.new("RGB", (100, 100)))
top_label_height = 0
left_label_width = 0

if has_col_labels:
    max_height = 0
    for label in col_labels:
        if label.strip():
            bbox = draw_temp.textbbox((0, 0), label, font=font_col)
            max_height = max(max_height, bbox[3] - bbox[1])
    top_label_height = max_height + 15

if has_row_labels:
    max_width = 0
    for label in row_labels:
        if label.strip():
            bbox = draw_temp.textbbox((0, 0), label, font=font_row)
            max_width = max(max_width, bbox[2] - bbox[0])
    left_label_width = max_width + 15

# Calculate final dimensions
grid_width = int(left_label_width + cols * resize_width + (cols - 1) * spacing)
grid_height = int(top_label_height + rows * resize_height + (rows - 1) * spacing)

# Create and draw grid
grid_img = Image.new("RGB", (grid_width, grid_height), color=(255, 255, 255))
draw = ImageDraw.Draw(grid_img)

# Draw column labels
if has_col_labels:
    for i, label in enumerate(col_labels):
        if label.strip():
            bbox = draw.textbbox((0, 0), label, font=font_col)
            text_w = bbox[2] - bbox[0]
            x = int(left_label_width + i * (resize_width + spacing) + (resize_width - text_w) / 2)
            y = 5
            draw.text((x, y), label, fill=(0, 0, 0), font=font_col)

# Draw row labels
if has_row_labels:
    for i, label in enumerate(row_labels):
        if label.strip():
            bbox = draw.textbbox((0, 0), label, font=font_row)
            text_h = bbox[3] - bbox[1]
            x = 5
            y = int(top_label_height + i * (resize_height + spacing) + (resize_height - text_h) / 2)
            draw.text((x, y), label, fill=(0, 0, 0), font=font_row)

# Paste images into grid
for idx, img in enumerate(images):
    row_idx, col_idx = divmod(idx, int(cols))
    x = int(left_label_width + col_idx * (resize_width + spacing))
    y = int(top_label_height + row_idx * (resize_height + spacing))
    grid_img.paste(img, (x, y))

# Display results
st.markdown("### 🎯 Generated Grid")
st.image(grid_img, caption="Your Custom Image Grid", use_container_width=True)

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
