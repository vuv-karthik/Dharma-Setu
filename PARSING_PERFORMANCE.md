# Quick comparison: Fast vs Hi-Res strategies

## Use Case Decision Matrix

### Use FAST strategy when:
- ✅ Development/testing iterations
- ✅ Quick prototyping
- ✅ Don't need table detection
- ✅ Simple text extraction is enough
- **Time: 1-2 minutes for 268 pages**

### Use HI-RES strategy when:
- ✅ Production data ingestion
- ✅ Need accurate table extraction
- ✅ Need proper section hierarchy
- ✅ Final, high-quality RAG database
- **Time: 15-25 minutes for 268 pages**

## Hybrid Approach (RECOMMENDED)

```python
# Development: Use fast-parsed data
python src/ingestion/parser_fast.py  # 2 min

# Production: Use hi-res for final ingestion  
python src/ingestion/parser.py       # 20 min
```

## Current Status
Your hi_res parser is working correctly - it's just computationally intensive.
The time estimates in the code were based on simpler PDFs. Legal documents 
with complex formatting take longer.

**Adjusted realistic estimate for Constitution (268 pages):**
- Total time: 20-25 minutes
- Per batch (after first): ~1 minute
- First batch (with model loading): ~3-5 minutes
