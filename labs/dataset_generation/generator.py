import os
import random
import json
import shutil
from pathlib import Path
from tqdm import tqdm
import pandas as pd
from huggingface_hub import HfApi, create_repo

# Import the generator modules
from bj_idcard_generator import main as generate_bj_idcard
from bj_passport_generator import main as generate_bj_passport
from civ_passport_generator import main as generate_civ_passport

def setup_directories():
    """Create necessary directories for the dataset."""
    # Create train directory for ImageFolder format
    os.makedirs("data/train", exist_ok=True)

    # Ensure the photo directory exists
    os.makedirs("id_photo", exist_ok=True)
    # Ensure the SVG files directory exists
    os.makedirs("svg_files", exist_ok=True)

def standardize_metadata(doc_data, doc_type):
    """Standardize metadata format across different document types."""
    standard_data = {
            "firstname": "",
            "surname": "",
            "birth_date": "",
            "place_of_birth": "",
            "nationality": "BEN" if "BJ" in doc_type else "CIV",
            "npi": "",
            "id_card": "",
            "expiry_date": "",
            "sex": "",
            "document_type": doc_type,
            "file_name": ""  # Changed to file_name for HuggingFace compatibility
    }

    # Map fields based on document type
    if "ID Card" in doc_type:
        standard_data.update({
                "firstname": doc_data.get("name", ""),
                "surname": doc_data.get("surname", ""),
                "birth_date": doc_data.get("birth_date_display", ""),
                "place_of_birth": doc_data.get("place_of_birth", ""),
                "npi": doc_data.get("npi", ""),
                "id_card": doc_data.get("id_card", ""),
                "expiry_date": doc_data.get("expiry_date_display", ""),
                "sexe": doc_data.get("gender", "")
        })
    else:  # Passport
        standard_data.update({
                "firstname": doc_data.get("name", ""),
                "surname": doc_data.get("surname", ""),
                "birth_date": doc_data.get("birth_date_display", ""),
                "place_of_birth": doc_data.get("place_of_birth", ""),
                "id_card": doc_data.get("passport_number", ""),
                "expiry_date": doc_data.get("expiry_date_display", ""),
                "sexe": doc_data.get("gender", "")
        })

    return standard_data

def generate_documents(count_per_type=10):
    """Generate specific count of each ID document type with standardized metadata."""
    setup_directories()

    metadata = []
    generators = [
            (generate_bj_idcard, "BJ ID Card"),
            (generate_bj_passport, "BJ Passport"),
            (generate_civ_passport, "CIV Passport")
    ]

    total_count = count_per_type * len(generators)
    doc_counter = 1

    # Generate documents for each type
    for generator_func, doc_type in generators:
        for i in tqdm(range(count_per_type), desc=f"Generating {doc_type}"):
            # Generate a document
            try:
                doc_data = generator_func(output_dir="dataset/images")

                # Extract the path to the generated image
                if "idcard_path" in doc_data:
                    image_path = doc_data["idcard_path"]
                elif "passport_number" in doc_data and isinstance(doc_data["passport_number"], str) and doc_data["passport_number"].endswith(".png"):
                    image_path = doc_data["output_path"]
                else:
                    continue  # Skip if we can't find the image path

                # Standardize metadata
                standard_data = standardize_metadata(doc_data, doc_type)

                # Add image filename to metadata
                standard_data["image_filename"] = os.path.basename(image_path)

                # Rename image file to a simpler format if needed
                new_image_name = f"document_{doc_counter:03d}.png"
                new_image_path = os.path.join("dataset/images", new_image_name)
                shutil.copy(image_path, new_image_path)
                standard_data["image_filename"] = new_image_name

                metadata.append(standard_data)
                doc_counter += 1

            except Exception as e:
                print(f"Error generating document: {e}")

    return metadata

def save_metadata(metadata):
    """Save metadata in multiple formats for HuggingFace compatibility."""
    # Save as JSON
    with open("dataset/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    # Save as CSV
    df = pd.DataFrame(metadata)
    df.to_csv("dataset/metadata.csv", index=False)

    # Save individual JSON files for each item
    for i, item in enumerate(metadata):
        with open(f"dataset/metadata/{i+1:03d}.json", "w") as f:
            json.dump(item, f, indent=2, default=str)

def create_dataset_card(count):
    """Create a README.md file for the HuggingFace dataset."""
    card_content = f"""# African ID Documents Dataset

    This dataset contains {count} synthetically generated African identification documents:
    - Benin ID Cards
    - Benin Passports
    - Côte d'Ivoire Passports

    ## Dataset Structure

    - `images/`: Contains the generated document images
    - `metadata.json`: Complete metadata for all documents
    - `metadata.csv`: Tabular metadata for all documents
    - `metadata/`: Individual JSON files for each document

    ## Metadata Fields

    All documents include the following standardized metadata:
    - firstname
    - surname
    - birth_date
    - place_of_birth
    - nationality
    - npi (when available)
    - id_card
    - expiry_date
    - sexe
    - document_type
    - image_filename

    ## Usage

    ```python
    from datasets import load_dataset

    dataset = load_dataset("YOUR_USERNAME/african-id-documents")
    License
    This dataset is synthetic and intended for research purposes only. """

    with open("dataset/README.md", "w") as f:
        f.write(card_content)

def upload_to_huggingface(repo_name, username=None):
    """Upload the dataset to Hugging Face."""
    try:
        # Initialize Hugging Face API
        api = HfApi()

        # Use token from environment variable or ask user
        token = os.environ.get("HF_TOKEN")
        if not token:
            token = input("Enter your Hugging Face API token: ")

        # No need to call set_access_token, just pass the token to each API call
        # api.set_access_token(token) - this line should be removed

        # Get username if not provided
        if not username:
            user_info = api.whoami(token=token)
            username = user_info.get("name")

        # Full repository name
        full_repo_name = f"{username}/{repo_name}"

        print(f"Creating repository: {full_repo_name}")
        try:
            create_repo(
                    repo_id=full_repo_name,
                    repo_type="dataset",
                    private=False,
                    token=token
            )
        except Exception as e:
            print(f"Repository might already exist or couldn't be created: {e}")

        # Load the dataset using the ImageFolder format
        print("Loading dataset with ImageFolder format...")
        dataset = load_dataset("imagefolder", data_dir="data")

        # Push to hub
        print(f"Pushing dataset to {full_repo_name}...")
        dataset.push_to_hub(full_repo_name, token=token)

        print(f"Dataset successfully uploaded to https://huggingface.co/datasets/{full_repo_name}")
        return True

    except Exception as e:
        print(f"Error uploading to Hugging Face: {e}")
        return False

def create_and_upload_dataset(count_per_type=10, repo_name="african-id-documents"):
    """Generate documents and upload them directly to HuggingFace."""
    print(f"Generating {count_per_type} documents for each type...")
    metadata = generate_documents(count_per_type=count_per_type)

    print("Saving metadata...")
    save_metadata(metadata)

    print("Uploading to Hugging Face...")
    upload_success = upload_to_huggingface(repo_name)

    if upload_success:
        print("Dataset successfully generated and uploaded to Hugging Face!")
    else:
        print("Dataset generated but upload failed. Files are available in the 'data' directory.")

    print(f"Total documents generated: {len(metadata)} ({count_per_type} per document type)")

if __name__ == "__main__":
    create_and_upload_dataset()