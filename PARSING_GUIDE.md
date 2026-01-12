# PDF Parsing Strategy Guide

## Overview
We have created multiple parsing scripts for legal documents with different trade-offs.

## Available Parsers

### 1. `parser_batch.py` ⭐ RECOMMENDED
**Best for:** Production use with progress monitoring

**Features:**
- Processes PDF in batches (default: 5 pages at a time)
- Real-time progress updates:
  - Current batch (e.g., "Batch 3/20")
  - Pages processed (e.g., "15/100 pages")
  - Percentage complete (e.g., "15.0%")
  - Estimated time remaining (e.g., "ETA: 8.5 min")
- Uses hi_res strategy with table detection
- Requires: Poppler installed

**Usage:**
```bash
python src/ingestion/parser_batch.py
```

**Output Example:**
```
14:24:22 - ======================================================================
14:24:22 - 📚 Starting parsing: Bharatiya_Nyaya_Sanhita_2023.pdf
14:24:22 - ======================================================================
14:24:22 - 📊 Total pages: 100
14:24:22 - 📦 Batch size: 5 pages
14:24:22- 🔢 Number of batches: 20
14:24:22 - ⏱️  Estimated time: 3.3-6.7 minutes
14:24:22 - ======================================================================

14:24:35 -    📄 Batch 1/20: Processing pages 1-5...
14:24:48 -    ✅ Batch 1/20: Extracted 45 elements in 13.2s
14:24:48 -    📈 Progress: 5.0% | 5/100 pages | ETA: 4.2 min

14:25:01 -    📄 Batch 2/20: Processing pages 6-10...
...
```

---

### 2. `parser.py`
**Best for:** One-shot complete processing

**Features:**
- Processes entire PDF at once
- No progress updates (silent until complete)
- Uses hi_res strategy with table detection
- Faster than batch mode (no overhead)
- Requires: Poppler installed

**Usage:**
```bash
python src/ingestion/parser.py
```

**Note:** Can take 10-20 minutes for large documents with no feedback

---

### 3. `parser_fast.py`
**Best for:** Quick testing without dependencies

**Features:**
- Uses 'fast' strategy (no poppler needed)
- Completes in 1-2 minutes
- **Limited accuracy** - no table detection
- All elements become generic "CompositeElement"

**Usage:**
```bash
python src/ingestion/parser_fast.py
```

**Trade-off:** Speed vs Accuracy

---

## Comparison Table

| Feature | parser_batch.py | parser.py | parser_fast.py |
|---------|----------------|-----------|----------------|
| **Progress Updates** | ✅ Real-time | ❌ None | ❌ None |
| **Table Detection** | ✅ Yes | ✅ Yes | ❌ No |
| **Header Detection** | ✅ Accurate | ✅ Accurate | ⚠️ Limited |
| **Speed (100 pages)** | ~5-10 min | ~8-15 min | ~1-2 min |
| **Requires Poppler** | ✅ Yes | ✅ Yes | ❌ No |
| **Best Use Case** | Production | Batch jobs | Quick tests |

---

## System Requirements

### For hi_res Strategy (parser.py, parser_batch.py):
1. **Poppler** must be installed
   - Location: `C:\poppler\poppler-25.12.0\Library\bin`
   - Added to PATH automatically by scripts

2. **Python packages** (already installed):
   - unstructured[all-docs]
   - pdf2image
   - onnxruntime

### For fast Strategy (parser_fast.py):
1. Only Python packages needed (no system dependencies)

---

## Recommended Workflow

### Development Phase:
```bash
# Use fast parser for quick iterations
python src/ingestion/parser_fast.py
```

### Production/Final Data Ingestion:
```bash
# Use batch parser for monitored, accurate extraction
python src/ingestion/parser_batch.py
```

### Batch Processing (Multiple PDFs):
```bash
# Use regular parser (no progress overhead)
python src/ingestion/parser.py
```

---

## Troubleshooting

### "PDFInfoNotInstalledError"
- **Cause:** Poppler not in PATH
- **Fix:** Scripts auto-add poppler to PATH. If fails, manually run:
  ```powershell
  $env:Path += ";C:\poppler\poppler-25.12.0\Library\bin"
  ```

### "ModuleNotFoundError: No module named 'unstructured'"
- **Cause:** Virtual environment not activated
- **Fix:** 
  ```powershell
  .venv\Scripts\Activate.ps1
  # OR use full path:
  .venv\Scripts\python.exe src/ingestion/parser_batch.py
  ```

### Parsing takes too long
- **Use batch parser** to monitor progress
- **Reduce batch size** for more frequent updates: Edit `BATCH_SIZE = 3` in parser_batch.py
- **Use fast parser** for development

---

## Next Steps

After parsing is complete, the extracted elements will be used for:
1. **Vector Database ingestion** (Qdrant)
2. **RAG retrieval** (semantic search)
3. **LangGraph agent workflows**

Current Status:
- ✅ Poppler installed
- ✅ Parser scripts created  
- 🔄 Waiting for parsing to complete OR user to choose strategy
