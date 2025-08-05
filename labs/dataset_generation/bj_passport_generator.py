import base64
import html
import random
from pathlib import Path
import time
import secrets


import cairosvg
from faker import Faker
from jinja2 import Template
from mrz.generator.td3 import TD3CodeGenerator

def load_random_photo(photo_dir="id_photo"):
    """Load a random photo from the specified directory and convert to base64."""
    photo_files = list(Path(photo_dir).glob("*.jpg"))
    if not photo_files:
        raise FileNotFoundError(f"No photos found in {photo_dir}")

    photo_path = photo_files[secrets.randbelow(len(photo_files))]
    with open(photo_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_passport_data(fake):
    """Generate random passport data using Faker."""
    data = {
            "name": fake.name(),
            "surname": fake.last_name(),
            "gender": fake.random_element(elements=('M', 'F')),
            "place_of_birth": fake.city(),
            "residence": fake.city(),
            "passport_number": fake.bothify(text='##??#####', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
            "height": round(random.uniform(1.5, 2.0), 2),
            "birth_date": fake.date_of_birth(minimum_age=18, maximum_age=65),
            "expiry_date": fake.date_between(start_date='today', end_date='+6y'),
            "issue_date": fake.date_this_decade()
    }
    return data

def format_dates(passport_data):
    """Format dates for MRZ and display."""
    return {
            "birth_date_mrz": passport_data["birth_date"].strftime("%y%m%d"),
            "expiry_date_mrz": passport_data["expiry_date"].strftime("%y%m%d"),
            "birth_date_display": passport_data["birth_date"].strftime("%d %m %Y"),
            "expiry_date_display": passport_data["expiry_date"].strftime("%d %m %Y"),
            "issue_date_display": passport_data["issue_date"].strftime("%d %m %Y")
    }

def prepare_mrz_names(surname, full_name, max_length=39):
    """Prepare names for MRZ by truncating if necessary and removing invalid characters."""
    # Remove invalid characters (keeping only letters, spaces, and hyphens)
    # The MRZ format requires specific characters and '<' for spaces
    def sanitize_for_mrz(text):
        # Keep only letters, spaces and hyphens
        return ''.join(c for c in text if c.isalpha() or c in ' -')

    surname = sanitize_for_mrz(surname)
    full_name = sanitize_for_mrz(full_name)
    given_names = full_name.replace(surname, "").strip()

    if len(surname) + len(given_names) + 2 <= max_length:  # +2 for "<<" separator
        return surname, given_names

    # Calculate max length for each part (prioritize surname)
    max_surname_length = min(len(surname), (max_length - 2) // 2)
    surname_mrz = surname[:max_surname_length]

    # Remaining space for given names
    max_given_length = max_length - 2 - len(surname_mrz)
    given_names_mrz = given_names[:max_given_length]

    return surname_mrz, given_names_mrz

def generate_mrz(passport_data, formatted_dates):
    """Generate MRZ code using passport data."""
    surname_mrz, given_names_mrz = prepare_mrz_names(
            passport_data["surname"],
            passport_data["name"]
    )

    return TD3CodeGenerator(
            "P",                            # Document type (Passport)
            "BEN",                          # Country code
            surname_mrz,                    # Surname (possibly truncated)
            given_names_mrz,                # Given names (possibly truncated)
            passport_data["passport_number"], # Document number
            "BEN",                          # Nationality
            formatted_dates["birth_date_mrz"],  # Birth date
            passport_data["gender"],        # Sex/Gender
            formatted_dates["expiry_date_mrz"]  # Expiry date
    )

def escape_data_for_xml(data):
    """Escape all string values for XML safety."""
    return {k: html.escape(str(v).upper()) if isinstance(v, str) else v
            for k, v in data.items()}

def render_passport_svg(template_path, data, photo_base64):
    """Render the passport SVG template with data."""
    try:
        with open(template_path) as f:
            template = Template(f.read())

        return template.render(
                MRZ_LINE1=data["mrz_line1"],
                MRZ_LINE2=data["mrz_line2"],
                NAME=data["surname"],  # Note: These appear to be swapped in the original
                SURNAME=data["name"],  # Note: These appear to be swapped in the original
                DATE_OF_BIRTH=data["birth_date_display"],
                GENDER=data["gender"],
                PLACE_OF_BIRTH=data["place_of_birth"],
                RESIDENCE=data["residence"],
                DATE_OF_ISSUE=data["issue_date_display"],
                DATE_OF_EXPIRY=data["expiry_date_display"],
                PASSPORT_NUMBER=data["passport_number"],
                HEIGHT=data["height"],
                PHOTO=photo_base64
        )
    except Exception as e:
        raise RuntimeError(f"Failed to render SVG template: {e}")

def main(template_path="svg_files/bj_passport.svg", output_dir="data", scale=3):
    """Main function to generate a passport image."""
    # Initialize Faker with multiple locales
    fake = Faker(['yo_NG', 'fr_FR', 'zu_ZA'])

    # Load random photo
    photo_base64 = load_random_photo()

    # Generate passport data
    passport_data = generate_passport_data(fake)
    formatted_dates = format_dates(passport_data)

    # Generate MRZ code
    mrz_generator = generate_mrz(passport_data, formatted_dates)
    mrz_lines = str(mrz_generator).split('\n')

    # Combine all data
    combined_data = {
            **passport_data,
            **formatted_dates,
            "mrz_line1": mrz_lines[0] if len(mrz_lines) > 0 else "",
            "mrz_line2": mrz_lines[1] if len(mrz_lines) > 1 else ""
    }

    # Escape data for XML
    escaped_data = escape_data_for_xml(combined_data)

    # Render SVG
    rendered_svg = render_passport_svg(template_path, escaped_data, photo_base64)

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)

    # Generate unique ID based on passport number and timestamp
    unique_id = f"{passport_data['passport_number']}_{int(time.time())}"

    # Create output path with unique ID
    output_path = Path(output_dir) / f"passport_{unique_id}.png"
    # Convert SVG to PNG
    cairosvg.svg2png(
            bytestring=rendered_svg.encode('utf-8'),
            write_to=str(output_path),
            scale=scale,
            unsafe=True
    )
    combined_data["passport_number"] = str(output_path)
    return combined_data

if __name__ == "__main__":
    print(main())