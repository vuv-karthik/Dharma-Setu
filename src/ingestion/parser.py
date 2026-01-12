import os
import sys
import time
import logging
import json
from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import elements_to_json

# Set poppler and tesseract paths for Windows if not already in PATH
if sys.platform == "win32":
    poppler_bin = r"C:\poppler\poppler-25.12.0\Library\bin"
    tesseract_bin = r"C:\Program Files\Tesseract-OCR"
    
    if os.path.exists(poppler_bin):
        os.environ["PATH"] = poppler_bin + os.pathsep + os.environ["PATH"]
    
    if os.path.exists(tesseract_bin):
        os.environ["PATH"] = tesseract_bin + os.pathsep + os.environ["PATH"]

# Setup logging for progress tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_pdf_page_count(file_path: str) -> int:
    """Get number of pages using pdfinfo."""
    import subprocess
    try:
        result = subprocess.run(['pdfinfo', file_path], capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
    except:
        return None

def parse_legal_pdf_batch(file_path: str, start_page: int, end_page: int, batch_num: int, total_batches: int):
    """Parse a batch of pages using FAST strategy."""
    logger.info(f"   📄 Batch {batch_num}/{total_batches}: Pages {start_page}-{end_page}...")
    batch_start = time.time()
    
    # Use FAST strategy for speed and reliability
    elements = partition_pdf(
        filename=file_path,
        strategy="fast", 
        pages=list(range(start_page, end_page + 1)),
        chunking_strategy="by_title",
        max_characters=2000,
        new_after_n_chars=1500,
        combine_text_under_n_chars=300,
    )
    
    logger.info(f"   ✅ Batch {batch_num}: {len(elements)} elements in {time.time()-batch_start:.1f}s")
    return elements

def parse_legal_pdf(file_path: str, batch_size: int = 50):
    """Parse PDF with batch processing and save results."""
    logger.info(f"\n{'='*70}")
    logger.info(f"📚 Parsing: {os.path.basename(file_path)}")
    logger.info(f"🚀 Strategy: FAST")
    logger.info(f"{'='*70}")
    
    page_count = get_pdf_page_count(file_path)
    if not page_count:
        logger.warning("⚠️  Using full document parsing (no page count available)")
        return partition_pdf(filename=file_path, strategy="fast", chunking_strategy="by_title")
    
    logger.info(f"📊 Pages: {page_count} | Batch size: {batch_size}")
    num_batches = (page_count + batch_size - 1) // batch_size
    
    overall_start = time.time()
    all_elements = []
    
    for batch_num in range(1, num_batches + 1):
        start_page = (batch_num - 1) * batch_size + 1
        end_page = min(batch_num * batch_size, page_count)
        
        try:
            batch_elements = parse_legal_pdf_batch(file_path, start_page, end_page, batch_num, num_batches)
            all_elements.extend(batch_elements)
            
            progress = (end_page / page_count) * 100
            elapsed = time.time() - overall_start
            eta = (elapsed / end_page) * (page_count - end_page)
            logger.info(f"   📈 {progress:.1f}% | ETA: {eta/60:.1f} min\n")
            
        except KeyboardInterrupt:
            logger.warning(f"\n⚠️  Interrupted at page {end_page}")
            break
            
    logger.info(f"✅ Completed in {(time.time()-overall_start):.1f} sec | {len(all_elements)} elements\n")
    return all_elements

def save_elements(elements, output_path):
    """Save elements to JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    elements_to_json(elements, filename=output_path)
    logger.info(f"💾 Saved {len(elements)} elements to {output_path}")

if __name__ == "__main__":
    target_files = [
        "data/raw/Constitution_of_India.pdf",
        "data/raw/Bharatiya_Nyaya_Sanhita_2023.pdf"
    ]
    
    all_docs_elements = []
    
    for raw_path in target_files:
        if os.path.exists(raw_path):
            try:
                # Use larger batch size for fast strategy
                elements = parse_legal_pdf(raw_path, batch_size=50)
                all_docs_elements.extend(elements)
            except Exception as e:
                logger.error(f"❌ Error: {e}")
        else:
            logger.error(f"❌ Not found: {raw_path}")
            
    # Save combined output
    if all_docs_elements:
        save_path = "data/processed/parsed_elements.json"
        save_elements(all_docs_elements, save_path)
        logger.info(f"\n🎉 Total extracted elements: {len(all_docs_elements)}")
    
    logger.info("🎉 Done!")
