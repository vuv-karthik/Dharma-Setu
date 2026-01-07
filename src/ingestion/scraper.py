import os
import requests
from typing import List, Dict

def download_pdf(url: str, filename: str, save_dir: str) -> bool:
    """
    Downloads a PDF from a URL and saves it to a specified directory.
    """
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)
    
    print(f"Downloading {filename} from {url}...")
    try:
        # Using a timeout and stream to handle large files
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Successfully saved to {filepath}")
        return True
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return False

def main():
    # Modular structure directories
    RAW_DATA_DIR = "data/raw"
    
    # Target documents using user-provided direct links
    documents: List[Dict[str, str]] = [
        {
            "name": "Constitution_of_India.pdf",
            "url": "https://www.indiacode.nic.in/bitstream/123456789/19151/1/constitution_of_india.pdf"
        },
        {
            "name": "Bharatiya_Nyaya_Sanhita_2023.pdf",
            "url": "https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf"
        }
    ]
    
    for doc in documents:
        download_pdf(doc["url"], doc["name"], RAW_DATA_DIR)

if __name__ == "__main__":
    main()
