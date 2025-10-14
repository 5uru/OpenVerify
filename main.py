import webbrowser
from pathlib import Path

from docling_core.types.doc import ImageRefMode
from docling_core.types.doc.document import DocTagsDocument, DoclingDocument
from mlx_vlm import load, stream_generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config
from transformers.image_utils import load_image

# Configuration
MODEL_PATH = "ibm-granite/granite-docling-258M-mlx"
PROMPT = "Convert this page to docling."
SHOW_IN_BROWSER = True

# Sample images (pick one...)
# SAMPLE_IMAGE = "https://huggingface.co/ibm-granite/granite-docling-258M/resolve/main/assets/new_arxiv.png"
# SAMPLE_IMAGE = "https://ibm.biz/docling-page-with-list"
SAMPLE_IMAGE = "https://ibm.biz/docling-page-with-table"

# Load model and processor
print("Loading model...")
model, processor = load(MODEL_PATH)
config = load_config(MODEL_PATH)

# Prepare input image and prompt
print("Preparing input...")
pil_image = load_image(SAMPLE_IMAGE)
formatted_prompt = apply_chat_template(processor, config, PROMPT, num_images=1)

# Generate DocTags output
print("Generating DocTags...\n")
output = ""
for token in stream_generate(
        model, processor, formatted_prompt, [pil_image], max_tokens=4096, verbose=False
):
    output += token.text
    print(token.text, end="")
    if "</doctag>" in token.text:
        break

print("\n\nProcessing output...")

# Create DoclingDocument from generated DocTags
doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([output], [pil_image])
doc = DoclingDocument.load_from_doctags(doctags_doc, document_name="Sample Document")

# Export to different formats
print("\nMarkdown output:\n")
print(doc.export_to_markdown())

# Save as HTML with embedded images
output_path = Path("./output.html")
doc.save_as_html(output_path, image_mode=ImageRefMode.EMBEDDED)
print(f"\nHTML saved to: {output_path}")

# Open in browser
if SHOW_IN_BROWSER:
    webbrowser.open(f"file:///{str(output_path.resolve())}")