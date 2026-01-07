import os
from unstructured.partition.pdf import partition_pdf

def parse_legal_pdf(file_path: str):
    """
    Refined parser for legal PDFs.
    Uses 'hi_res' for layout analysis to distinguish between Titles, Tables, and Body Text.
    """
    print(f"Parsing {file_path} with structural awareness...")
    
    # 'hi_res' strategy is essential for detecting tables and complex layouts
    elements = partition_pdf(
        filename=file_path,
        strategy="hi_res",
        
        # Table detection
        infer_table_structure=True,
        
        # Chunking by title ensures that a Section or Chapter header 
        # initiates a new logical block, preventing text bleeding.
        chunking_strategy="by_title",
        max_characters=2000,
        new_after_n_chars=1500,
        combine_text_under_n_chars=300,
        
        # Additional settings for legal text quality
        multipage_sections=True
    )
    return elements

def summarize_parsing(elements):
    """Utility to show the distribution of detected elements."""
    element_counts = {}
    for el in elements:
        category = el.category
        element_counts[category] = element_counts.get(category, 0) + 1
    
    print("\n--- Parsing Result Summary ---")
    for category, count in element_counts.items():
        print(f"{category}: {count}")
    print("------------------------------\n")

# Example Usage
if __name__ == "__main__":
    # Update paths to match the downloaded files
    target_files = [
        "data/raw/Constitution_of_India.pdf",
        "data/raw/Bharatiya_Nyaya_Sanhita_2023.pdf"
    ]
    
    for raw_path in target_files:
        if os.path.exists(raw_path):
            structured_data = parse_legal_pdf(raw_path)
            summarize_parsing(structured_data)
            
            # Peek at the first Table if detected
            tables = [el for el in structured_data if el.category == "Table"]
            if tables:
                print(f"Found {len(tables)} tables. Sample HTML from first table:")
                print(tables[0].metadata.text_as_html[:500] + "...")
        else:
            print(f"File not found: {raw_path}")
