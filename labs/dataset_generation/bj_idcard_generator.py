import base64
import html
import random
from pathlib import Path
import time
import secrets
from PIL import Image
import io

import cairosvg
from faker import Faker
from jinja2 import Template
from mrz.generator.mrva import MRVACodeGenerator

def load_random_photo(photo_dir="id_photo"):
    """Load a random photo from the specified directory and convert to base64."""
    photo_files = list(Path(photo_dir).glob("*.jpg"))
    if not photo_files:
        raise FileNotFoundError(f"No photos found in {photo_dir}")

    photo_path = photo_files[secrets.randbelow(len(photo_files))]
    with open(photo_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_idcard_data(fake):
    """Generate random ID card data using Faker."""
    data = {
            "name": fake.name(),
            "surname": fake.last_name(),
            "gender": fake.random_element(elements=('M', 'F')),
            "place_of_birth": fake.city(),
            "residence": fake.city(),
            "id_card": fake.bothify(text='#########'),
            "npi": fake.bothify(text='#########'),
            "birth_date": fake.date_of_birth(minimum_age=18, maximum_age=65),
            "expiry_date": fake.date_between(end_date='+6y'),
    }
    return data

def format_dates(idcard_data):
    """Format dates for MRZ and display."""
    return {
            "birth_date_mrz": idcard_data["birth_date"].strftime("%y%m%d"),
            "expiry_date_mrz": idcard_data["expiry_date"].strftime("%y%m%d"),
            "birth_date_display": idcard_data["birth_date"].strftime("%d %m %Y"),
            "expiry_date_display": idcard_data["expiry_date"].strftime("%d %m %Y"),
    }

def prepare_mrz_names(surname, full_name, max_length=39):
    """Prepare names for MRZ by truncating if necessary and removing invalid characters."""
    def sanitize_for_mrz(text):
        return ''.join(c for c in text if c.isalpha() or c in ' -')

    surname = sanitize_for_mrz(surname)
    full_name = sanitize_for_mrz(full_name)
    given_names = full_name.replace(surname, "").strip()

    if len(surname) + len(given_names) + 2 <= max_length:  # +2 for "<<" separator
        return surname, given_names

    max_surname_length = min(len(surname), (max_length - 2) // 2)
    surname_mrz = surname[:max_surname_length]

    max_given_length = max_length - 2 - len(surname_mrz)
    given_names_mrz = given_names[:max_given_length]

    return surname_mrz, given_names_mrz

def generate_mrz(idcard_data, formatted_dates):
    """Generate MRZ code using ID card data."""
    surname_mrz, given_names_mrz = prepare_mrz_names(
            idcard_data["surname"],
            idcard_data["name"]
    )

    return MRVACodeGenerator(
            "V",                           # Document type
            "BEN",                         # Country code
            surname_mrz,                   # Surname
            given_names_mrz,               # Given names
            idcard_data["id_card"],        # Document number
            "BEN",                         # Nationality
            formatted_dates["birth_date_mrz"],  # Birth date
            idcard_data["gender"],         # Gender
            formatted_dates["expiry_date_mrz"]  # Expiry date
    )

def escape_data_for_xml(data):
    """Escape all string values for XML safety."""
    return {k: html.escape(str(v).upper()) if isinstance(v, str) else v
            for k, v in data.items()}

def render_front_svg(template_path, data, photo_base64):
    """Render the ID card front SVG template with data."""
    try:
        with open(template_path) as f:
            template = Template(f.read())

        return template.render(
                NAME=data["surname"],
                FIRSTNAME=data["name"],
                DATE_OF_BIRTH=data["birth_date_display"],
                PLACE_OF_BIRTH=data["place_of_birth"],
                DATE_OF_EXPIRY=data["expiry_date_display"],
                CARD_NUMBER=data["id_card"],
                PHOTO=photo_base64,
                ID_NUMBER=data["npi"],
        )
    except Exception as e:
        raise RuntimeError(f"Failed to render front SVG template: {e}")

def render_back_svg(template_path, data):
    """Render the ID card back SVG template with data."""
    try:
        with open(template_path) as f:
            template = Template(f.read())

        return template.render(
                MRZ_LINE1=data["mrz_line1"],
                MRZ_LINE2=data["mrz_line2"],
                GENDER=data["gender"]
        )
    except Exception as e:
        raise RuntimeError(f"Failed to render back SVG template: {e}")

def svg_to_pil_image(svg_content, scale=3):
    """Convert SVG content to PIL Image."""
    png_data = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), scale=scale, unsafe=True)
    return Image.open(io.BytesIO(png_data))

def main(front_template="svg_files/bj_idcard_front.svg",
         back_template="svg_files/bj_idcard_back.svg",
         output_dir="data", scale=3):
    """Main function to generate an ID card image with front and back sides."""
    # Initialize Faker with multiple locales
    fake = Faker(['yo_NG', 'fr_FR', 'zu_ZA'])

    # Load random photo
    photo_base64 = load_random_photo()

    # Generate ID card data
    idcard_data = generate_idcard_data(fake)
    formatted_dates = format_dates(idcard_data)

    # Generate MRZ code
    mrz_generator = generate_mrz(idcard_data, formatted_dates)
    mrz_lines = str(mrz_generator).split('\n')

    # Combine all data
    combined_data = {
            **idcard_data,
            **formatted_dates,
            "mrz_line1": mrz_lines[0] if len(mrz_lines) > 0 else "",
            "mrz_line2": mrz_lines[1] if len(mrz_lines) > 1 else ""
    }

    # Escape data for XML
    escaped_data = escape_data_for_xml(combined_data)

    # Render SVG
    rendered_svg_front = render_front_svg(front_template, escaped_data, photo_base64)
    rendered_svg_back = render_back_svg(back_template, escaped_data)

    # Convert SVGs to PIL Images
    front_image = svg_to_pil_image(rendered_svg_front, scale)
    back_image = svg_to_pil_image(rendered_svg_back, scale)

    # Create a new image with both front and back
    width = max(front_image.width, back_image.width)
    height = front_image.height + back_image.height + 10  # 10px gap between images
    combined_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))

    # Paste front and back images
    combined_image.paste(front_image, (0, 0))
    combined_image.paste(back_image, (0, front_image.height + 10))

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)

    # Generate unique ID based on ID card number and timestamp
    unique_id = f"{idcard_data['id_card']}_{int(time.time())}"

    # Create output path with unique ID
    output_path = Path(output_dir) / f"idcard_{unique_id}.png"

    # Save the combined image
    combined_image.save(str(output_path))

    combined_data["idcard_path"] = str(output_path)
    return combined_data

if __name__ == "__main__":
    print(main())