# PDF MCQ Parser - Automated Question Extraction System

## Overview
This system automatically extracts Multiple Choice Questions (MCQs) from PDF files and generates a structured CSV output. It includes intelligent tracking to process only new or modified PDFs.

## Features
- ✅ **Automatic PDF Processing**: Scans a folder for PDF files
- ✅ **OCR Support**: Handles both text-based and image-based (scanned) PDFs
- ✅ **Incremental Updates**: Tracks which PDFs have been processed
- ✅ **Smart Parsing**: Extracts Question 1 MCQs with roman numeral parts (i, ii, iii, etc.)
- ✅ **CSV Output**: Generates structured data with Subject, Question Number, Question, and 4 Options
- ✅ **Batch Processing**: Can process multiple PDFs in one run

## Files Generated

### 1. `mcq_questions.csv`
The main output file containing all extracted MCQs with the following columns:
- **Subject**: Mathematics, Physics, Chemistry, etc.
- **Question_No**: Question identifier (e.g., Q1-i), Q1-ii))
- **Question**: The question text
- **Option_A**: First option
- **Option_B**: Second option
- **Option_C**: Third option
- **Option_D**: Fourth option

### 2. `parsed_pdfs.json`
Tracking file that maintains a record of processed PDFs and their modification times.

## How It Works

### Initial Setup
The script is located at: `/home/claude/pdf_mcq_parser.py`

### Configuration
```python
PDF_FOLDER = "/mnt/user-data/uploads"       # Where PDFs are located
OUTPUT_CSV = "/mnt/user-data/outputs/mcq_questions.csv"  # Output file
TRACKING_FILE = "/home/claude/parsed_pdfs.json"  # Tracking file
```

### Running the Parser

#### First Run (Process All PDFs)
```bash
python3 /home/claude/pdf_mcq_parser.py
```

This will:
1. Scan the PDF folder
2. Process all PDFs found
3. Extract Question 1 MCQs
4. Generate the CSV file
5. Create tracking file

#### Subsequent Runs (Process Only New PDFs)
Simply run the same command:
```bash
python3 /home/claude/pdf_mcq_parser.py
```

The script will:
1. Check which PDFs are new or modified
2. Process only those PDFs
3. Append results to existing CSV
4. Update the tracking file

#### Output Example
```
Found 1 new PDF(s) to process...

Processing: ICSE_Grade10_Maths_2025_1.pdf
  PDF appears to be image-based, using OCR...
    OCR processing page 1...
    OCR processing page 2...
    ...
  Subject: Mathematics
  Found 11 MCQs in Question 1

Processing complete! Results saved to /mnt/user-data/outputs/mcq_questions.csv
```

## Workflow for Adding New PDFs

1. **Add PDF files** to `/mnt/user-data/uploads/`
2. **Run the script**: `python3 /home/claude/pdf_mcq_parser.py`
3. **Check the output**: New MCQs will be appended to `mcq_questions.csv`

## Parsing Logic

### Question 1 Detection
The parser looks for:
- "Question 1" header
- "Choose the correct answer" instruction
- Section ends at "Question 2" or after reasonable content length

### MCQ Part Detection
- Identifies roman numerals: i), ii), iii), iv), v), vi), vii), viii), ix), x), xi), xii), xiii), xiv), xv)
- Extracts question text before options
- Parses options marked as (a), (b), (c), (d)

### OCR Handling
For image-based PDFs:
- Converts first 10 pages to images
- Applies OCR (Optical Character Recognition)
- Processes extracted text

## Tracking System

The `parsed_pdfs.json` file maintains:
```json
{
  "ICSE_Grade10_Maths_2025_1.pdf": 1702992368.5,
  "Physics_Sample_Paper.pdf": 1702995123.8
}
```

Each entry stores:
- **Key**: PDF filename
- **Value**: Last modification timestamp

## Resetting the System

### To Re-process All PDFs
Delete the tracking file:
```bash
rm /home/claude/parsed_pdfs.json
```

### To Start Fresh (Clear Everything)
```bash
rm /home/claude/parsed_pdfs.json
rm /mnt/user-data/outputs/mcq_questions.csv
```

## Advanced Usage

### Processing Specific PDF Folder
Edit the script to change the PDF folder:
```python
PDF_FOLDER = "/path/to/your/pdfs"
```

### Changing Output Location
```python
OUTPUT_CSV = "/path/to/output.csv"
```

### Customizing MCQ Detection
Modify the `parse_question_1_mcqs()` method in the script to:
- Change question number (e.g., Question 2, Question 3)
- Adjust roman numeral patterns
- Modify option detection logic

## Troubleshooting

### No MCQs Found
- Check if PDF contains Question 1
- Verify the question format matches expected pattern
- For image PDFs, ensure OCR is working (check console output)

### Incorrect Parsing
- OCR may introduce errors in image-based PDFs
- Check the extracted text manually
- May need to adjust parsing patterns for specific PDF formats

### Performance
- OCR processing is slower (1-2 seconds per page)
- Text-based PDFs process almost instantly
- Large batches: expect ~30-60 seconds per image-based PDF

## Sample Output

| Subject | Question_No | Question | Option_A | Option_B | Option_C | Option_D |
|---------|------------|----------|----------|----------|----------|----------|
| Mathematics | Q1-i) | If A = [[5,3],[-1,2]], find (A - 2I). | [[3,3],[-1,0]] | [[7,3],[-1,4]] | [[4,3],[-1,1]] | [[5,1],[-3,2]] |
| Mathematics | Q1-ii) | Find the value of m if 2/3 is a solution... | -2√6 | -5 | -2√3 | -6 |

## System Requirements
- Python 3.x
- Libraries: pypdf, pdf2image, pytesseract, PIL
- Tesseract OCR engine (for image-based PDFs)

## Version
Current Version: 1.0

## Notes
- The system currently processes only Question 1 MCQs
- Can be extended to handle other question types
- Designed for ICSE, CBSE, and similar exam paper formats
