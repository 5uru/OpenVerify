from jinja2 import Template
import cairosvg
from faker import Faker
from mrz.generator.td3 import TD3CodeGenerator
import html

fake = Faker(['yo_NG', 'fr_FR', 'zu_ZA'])

# Generate basic passport data
NAME = fake.name()
SURNAME = fake.last_name()
GENDER = fake.random_element(elements=('M', 'F'))
PLACE_OF_BIRTH = fake.city()
RESIDENCE = fake.city()
PASSPORT_NUMBER = fake.bothify(text='??#######', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ')

# Generate dates as objects first to maintain consistency
birth_date_obj = fake.date_of_birth(minimum_age=18, maximum_age=65)
expiry_date_obj = fake.date_between(start_date='today', end_date='+10y')
issue_date_obj = fake.date_this_decade()

# Format for MRZ (YYMMDD)
BIRTH_DATE_MRZ = birth_date_obj.strftime("%y%m%d")
DATE_OF_EXPIRY_MRZ = expiry_date_obj.strftime("%y%m%d")

# Format for display (DD MM YYYY)
BIRTH_DATE_DISPLAY = birth_date_obj.strftime("%d %m %Y")
DATE_OF_EXPIRY_DISPLAY = expiry_date_obj.strftime("%d %m %Y")
DATE_OF_ISSUE_DISPLAY = issue_date_obj.strftime("%d %m %Y")

# Get given names (everything before surname)
given_names = NAME.replace(SURNAME, "").strip()

# Generate MRZ code using TD3 format with proper MRZ date format
mrz_generator = TD3CodeGenerator(
        "P",                # Document type (Passport)
        "BEN",              # Country code
        SURNAME,            # Surname
        given_names,        # Given names
        PASSPORT_NUMBER,    # Document number
        "BEN",              # Nationality
        BIRTH_DATE_MRZ,     # Birth date (YYMMDD format)
        GENDER,             # Sex/Gender
        DATE_OF_EXPIRY_MRZ  # Expiry date (YYMMDD format)
)

# Load SVG template
with open("bj_passport.svg") as f:
    template = Template(f.read())

# Get the MRZ string representation
mrz_code = str(mrz_generator)
mrz_lines = mrz_code.split('\n')

# Escape all string values for XML safety
NAME = html.escape(NAME)
SURNAME = html.escape(SURNAME)
PLACE_OF_BIRTH = html.escape(PLACE_OF_BIRTH)
RESIDENCE = html.escape(RESIDENCE)
PASSPORT_NUMBER = html.escape(PASSPORT_NUMBER)
MRZ_LINE1 = html.escape(mrz_lines[0] if len(mrz_lines) > 0 else "")
MRZ_LINE2 = html.escape(mrz_lines[1] if len(mrz_lines) > 1 else "")

# Render template with display-formatted dates
rendered_svg = template.render(
        MRZ_LINE1 = MRZ_LINE1,
        MRZ_LINE2 = MRZ_LINE2,
        NAME = NAME,
        SURNAME = SURNAME,
        BIRTH_DATE = BIRTH_DATE_DISPLAY,  # Use display format with spaces
        GENDER = GENDER,
        PLACE_OF_BIRTH = PLACE_OF_BIRTH,
        RESIDENCE = RESIDENCE,
        DATE_OF_ISSUE = DATE_OF_ISSUE_DISPLAY,  # Use display format with spaces
        DATE_OF_EXPIRY = DATE_OF_EXPIRY_DISPLAY,  # Use display format with spaces
        PASSPORT_NUMBER = PASSPORT_NUMBER
)

# Convert SVG to PNG
output_png = "output.png"
cairosvg.svg2png(
        bytestring=rendered_svg.encode('utf-8'),
        write_to=output_png,
        output_width=512,
        output_height=512,
        scale=1.5,
        unsafe=True
)

print(f"Image saved to {output_png}")