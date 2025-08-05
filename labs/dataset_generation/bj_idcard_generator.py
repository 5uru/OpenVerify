import base64
import html
import io
import time
from pathlib import Path
import secrets

import cairosvg
from faker import Faker
from jinja2 import Template
from mrz.generator.mrva import MRVACodeGenerator
from PIL import Image

def main(front_template="svg_files/bj_idcard_front.svg",
                           back_template="svg_files/bj_idcard_back.svg",
                           output_dir="data",
                           photo_dir="id_photo",
                           scale=3):
    """Generate a single ID card image with front and back sides."""
    # Ensure output directory exists
    Path(output_dir).mkdir(exist_ok=True)

    # Initialize Faker with multiple locales
    fake = Faker(['yo_NG', 'fr_FR', 'zu_ZA'])

    # Load random photo
    photo_files = list(Path(photo_dir).glob("*.jpg"))
    if not photo_files:
        raise FileNotFoundError(f"No photos found in {photo_dir}")
    photo_path = photo_files[secrets.randbelow(len(photo_files))]
    with open(photo_path, "rb") as image_file:
        photo_base64 = base64.b64encode(image_file.read()).decode('utf-8')

    # Generate ID card data
    idcard_data = {
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

    # Format dates
    birth_date = idcard_data["birth_date"]
    expiry_date = idcard_data["expiry_date"]
    formatted_dates = {
            "birth_date_mrz": birth_date.strftime("%y%m%d"),
            "expiry_date_mrz": expiry_date.strftime("%y%m%d"),
            "birth_date_display": birth_date.strftime("%d %m %Y"),
            "expiry_date_display": expiry_date.strftime("%d %m %Y"),
    }

    # Prepare names for MRZ
    surname = idcard_data["surname"]
    full_name = idcard_data["name"]
    max_length = 39

    # Clean names for MRZ
    valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ -')
    surname = ''.join(c for c in surname if c in valid_chars)
    full_name = ''.join(c for c in full_name if c in valid_chars)
    given_names = full_name.replace(surname, "", 1).strip()

    if len(surname) + len(given_names) + 2 > max_length:
        max_surname_length = min(len(surname), (max_length - 2) // 2)
        surname_mrz = surname[:max_surname_length]
        max_given_length = max_length - 2 - len(surname_mrz)
        given_names_mrz = given_names[:max_given_length]
    else:
        surname_mrz, given_names_mrz = surname, given_names

    # Generate MRZ code
    mrz_generator = MRVACodeGenerator(
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
    mrz_lines = str(mrz_generator).split('\n')

    # Combine all data
    combined_data = {
            **idcard_data,
            **formatted_dates,
            "mrz_line1": mrz_lines[0] if mrz_lines else "",
            "mrz_line2": mrz_lines[1] if len(mrz_lines) > 1 else ""
    }

    # Escape data for XML
    escaped_data = {k: html.escape(str(v).upper()) if isinstance(v, str) else v
                    for k, v in combined_data.items()}

    # Render front SVG
    with open(front_template) as f:
        front_template = Template(f.read())
    rendered_svg_front = front_template.render(
            NAME=escaped_data["surname"],
            FIRSTNAME=escaped_data["name"],
            DATE_OF_BIRTH=escaped_data["birth_date_display"],
            PLACE_OF_BIRTH=escaped_data["place_of_birth"],
            DATE_OF_EXPIRY=escaped_data["expiry_date_display"],
            CARD_NUMBER=escaped_data["id_card"],
            PHOTO=photo_base64,
            ID_NUMBER=escaped_data["npi"],
    )

    # Render back SVG
    with open(back_template) as f:
        back_template = Template(f.read())
    rendered_svg_back = back_template.render(
            MRZ_LINE1=escaped_data["mrz_line1"],
            MRZ_LINE2=escaped_data["mrz_line2"],
            GENDER=escaped_data["gender"]
    )

    # Convert SVGs to PNG images
    png_front = cairosvg.svg2png(bytestring=rendered_svg_front.encode('utf-8'), scale=scale, unsafe=True)
    png_back = cairosvg.svg2png(bytestring=rendered_svg_back.encode('utf-8'), scale=scale, unsafe=True)

    # Convert to PIL Images
    front_image = Image.open(io.BytesIO(png_front))
    back_image = Image.open(io.BytesIO(png_back))

    # Create combined image
    width = max(front_image.width, back_image.width)
    height = front_image.height + back_image.height + 10  # 10px gap
    combined_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))

    # Paste images
    combined_image.paste(front_image, (0, 0))
    combined_image.paste(back_image, (0, front_image.height + 10))

    # Save image
    unique_id = f"{idcard_data['id_card']}_{int(time.time())}"
    output_path = Path(output_dir) / f"idcard_{unique_id}.png"
    combined_image.save(str(output_path), optimize=True)

    return {
            "idcard_path": str(output_path),
            "id_card": idcard_data["id_card"],
            "name": idcard_data["name"],
            "surname": idcard_data["surname"],
            "birth_date": idcard_data["birth_date"],
            "place_of_birth": idcard_data["place_of_birth"],
            "npi": idcard_data["npi"],
            "expiry_date": idcard_data["expiry_date"],
            "sex": idcard_data["gender"]
    }

if __name__ == "__main__":
    start_time = time.time()
    result = main()
    end_time = time.time()
    print(f"Generated ID card: {result['idcard_path']}")
    print(f"Name: {result['surname']}, {result['name']}")
    print(f"ID: {result['id_card']}")
    print(f"Passport generated in {end_time - start_time:.3f} seconds")