import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
from streamlit_sortables import sort_items

st.title("🧱 Custom Image Grid Maker")

# Upload section
uploaded_files = st.file_uploader("Upload Images", accept_multiple_files=True, type=["png", "jpg", "jpeg"])
if not uploaded_files:
    st.stop()

file_names = [f.name for f in uploaded_files]

# Grid setup
cols = st.number_input("Number of Columns", min_value=1, value=3)
rows = st.number_input("Number of Rows", min_value=1, value=5)
resize_width = st.number_input("Resize Width (px)", min_value=10, value=256)
resize_height = st.number_input("Resize Height (px)", min_value=10, value=256)
spacing = st.number_input("Spacing Between Images (px)", min_value=0, value=10)

# Font config
st.markdown("### 🔤 Font Settings")
font_file = st.file_uploader("Optional: Upload a .ttf Font File", type=["ttf"])
col_font_size = st.number_input("Column Label Font Size", min_value=8, max_value=64, value=16)
row_font_size = st.number_input("Row Label Font Size", min_value=8, max_value=64, value=16)

# Load fonts
try:
    if font_file is not None:
        font_bytes = font_file.read()
        font_col = ImageFont.truetype(io.BytesIO(font_bytes), col_font_size)
        font_row = ImageFont.truetype(io.BytesIO(font_bytes), row_font_size)
    else:
        font_col = ImageFont.truetype("DejaVuSans.ttf", col_font_size)
        font_row = ImageFont.truetype("DejaVuSans.ttf", row_font_size)
except:
    st.warning("⚠️ Font fallback used. Upload a .ttf file for correct sizing.")
    font_col = font_row = ImageFont.load_default()

# Column & Row Labels
# Label toggles
show_col_labels = st.checkbox("Show Column Labels?", value=True)
show_row_labels = st.checkbox("Show Row Labels?", value=False)

# Conditional label inputs
if show_col_labels:
    st.markdown("### 🏷️ Column Labels")
    col_labels = [st.text_input(f"Label for Column {i+1}", value="") for i in range(int(cols))]
else:
    col_labels = [""] * int(cols)

if show_row_labels:
    st.markdown("### 🏷️ Row Labels")
    row_labels = [st.text_input(f"Label for Row {i+1}", value="") for i in range(int(rows))]
else:
    row_labels = [""] * int(rows)


# Image reordering
# Validate image count
expected_count = int(rows * cols)
if len(uploaded_files) != expected_count:
    st.error(f"❌ You uploaded {len(uploaded_files)} images, but a {rows}×{cols} grid needs {expected_count}.")
    st.stop()

file_names = [f.name for f in uploaded_files]
name_to_file = {f.name: f for f in uploaded_files}

# Drag to reorder using filenames
st.markdown("### 🔃 Drag to Reorder (use names)")
sorted_names = sort_items(file_names, direction="vertical")

if not sorted_names or len(sorted_names) != expected_count:
    st.warning("⚠️ Please drag all images to define the full order.")
    st.stop()

# Final sorted images
images = [Image.open(name_to_file[name]).convert("RGB").resize((resize_width, resize_height)) for name in sorted_names]



# Label flags
has_col_labels = any(label.strip() for label in col_labels)
has_row_labels = any(label.strip() for label in row_labels)

# Text space estimation
draw_temp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
top_label_height = max([draw_temp.textbbox((0, 0), txt, font=font_col)[3] for txt in col_labels if txt.strip()] + [0]) + 10 if has_col_labels else 0
left_label_width = max([draw_temp.textbbox((0, 0), txt, font=font_row)[2] for txt in row_labels if txt.strip()] + [0]) + 10 if has_row_labels else 0

# Final canvas size
grid_width = left_label_width + cols * resize_width + (cols - 1) * spacing
grid_height = top_label_height + rows * resize_height + (rows - 1) * spacing

# Create output image
grid_img = Image.new("RGB", (grid_width, grid_height), color=(255, 255, 255))
draw = ImageDraw.Draw(grid_img)

# Draw column labels
if has_col_labels:
    for i, label in enumerate(col_labels):
        if not label.strip():
            continue
        bbox = draw.textbbox((0, 0), label, font=font_col)
        text_w = bbox[2] - bbox[0]
        x = int(left_label_width + i * (resize_width + spacing) + (resize_width - text_w) / 2)
        draw.text((x, 0), label, fill=(0, 0, 0), font=font_col)

# Draw row labels
if has_row_labels:
    for i, label in enumerate(row_labels):
        if not label.strip():
            continue
        bbox = draw.textbbox((0, 0), label, font=font_row)
        text_h = bbox[3] - bbox[1]
        y = int(top_label_height + i * (resize_height + spacing) + (resize_height - text_h) / 2)
        draw.text((0, y), label, fill=(0, 0, 0), font=font_row)

# Paste images
for idx, img in enumerate(images):
    r, c = divmod(idx, cols)
    x = int(left_label_width + c * (resize_width + spacing))
    y = int(top_label_height + r * (resize_height + spacing))
    grid_img.paste(img, (x, y))

# Display & download
st.image(grid_img, caption="Generated Grid", use_column_width=True)

buf = io.BytesIO()
grid_img.save(buf, format="PNG")
st.download_button("📥 Download Grid Image", buf.getvalue(), file_name="image_grid.png", mime="image/png")
