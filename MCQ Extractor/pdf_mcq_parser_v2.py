import os
import json
import csv
import re
from pathlib import Path
from pypdf import PdfReader
import pdf2image
import pytesseract

class PDFMCQParser:
    def __init__(self, pdf_folder, output_csv, tracking_file="parsed_pdfs.json"):
        self.pdf_folder = pdf_folder
        self.output_csv = output_csv
        self.tracking_file = tracking_file
        self.parsed_pdfs = self.load_tracking()
        
    def load_tracking(self):
        """Load the tracking file to see which PDFs have been parsed"""
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_tracking(self):
        """Save the tracking file"""
        with open(self.tracking_file, 'w') as f:
            json.dump(self.parsed_pdfs, f, indent=2)
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF using both direct extraction and OCR if needed"""
        try:
            # First try direct text extraction
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            # If we got meaningful text, return it
            if len(text.strip()) > 100:
                return text
            
            # Otherwise, use OCR
            print("  PDF appears to be image-based, using OCR...")
            return self.extract_text_with_ocr(pdf_path)
            
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")
            return ""
    
    def extract_text_with_ocr(self, pdf_path):
        """Extract text from image-based PDF using OCR"""
        try:
            # Convert all PDF pages to images (for solutions too)
            images = pdf2image.convert_from_path(pdf_path)
            
            text = ""
            for i, image in enumerate(images):
                print(f"    OCR processing page {i+1}/{len(images)}...")
                # Perform OCR
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"
            
            return text
            
        except Exception as e:
            print(f"  OCR Error: {e}")
            return ""
    
    def extract_subject(self, text):
        """Extract subject from PDF text"""
        # Look for subject name in the header
        subject_match = re.search(r'(Mathematics|Physics|Chemistry|Biology|English|Science|Maths)', text, re.IGNORECASE)
        if subject_match:
            subject = subject_match.group(1).capitalize()
            if subject.lower() == "maths":
                return "Mathematics"
            return subject
        return "Unknown"
    
    def extract_solutions(self, text):
        """Extract solutions/answers from the PDF"""
        solutions = {}
        
        # Look for solution section - multiple patterns to catch different formats
        solution_patterns = [
            r'(?:Solution|Answer)[s]?\s.*?(?:SECTION\s*A|Question\s*1)',
            r'Answers?\s*.*?Answer\s*1',
        ]
        
        solution_section = None
        for pattern in solution_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                # Get extended context - from match to Question 2 or reasonable length
                start = match.start()
                q2_match = re.search(r'(?:Question\s*2|SECTION\s*B)', text[start:], re.IGNORECASE)
                if q2_match:
                    solution_section = text[start:start + q2_match.start()]
                else:
                    solution_section = text[start:start + 15000]  # Extended for solutions
                break
        
        if not solution_section:
            return solutions
        
        # Extract individual question solutions
        # Pattern variations: (i) Option (d) is correct, i) (d), (i) d, etc.
        patterns = [
            # Format: (i) Option (d) is correct
            r'\(?\s*(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{1,3}|xiv|xv)\s*\)?\s*Option\s*\(?([a-d])\)?\s*is\s*correct',
            # Format: (i) (d)
            r'\(?\s*(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{1,3}|xiv|xv)\s*\)\s*\(?([a-d])\)?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, solution_section, re.IGNORECASE)
            for roman, answer in matches:
                # Normalize roman numeral
                roman_key = roman.lower().strip() + ')'
                answer_upper = answer.upper()
                solutions[roman_key] = f"Option {answer_upper}"
        
        return solutions
    
    def parse_question_1_mcqs(self, text, solutions):
        """Parse Question 1 MCQs from the PDF text"""
        mcqs = []
        
        # Find Question 1 section (handle SECTION-A and "Select/Choose the correct answer")
        q1_pattern = r'(?:SECTION\s*[-–]?\s*A\s*)?(?:\d+\.\s*)?(?:Question\s*1\b.*?|Select\s+the\s+correct\s+answer.*?|Choose\s+one\s+correct\s+answer.*?)(?:correct\s+answer[s]?|given\s+options)?'
        q1_match = re.search(q1_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if not q1_match:
            # Fallback: start at Section A if present
            q1_match = re.search(r'SECTION\s*[-–]?\s*A', text, re.IGNORECASE)
        
        if not q1_match:
            print("  Could not find Question 1 header")
            return mcqs
        
        # Extract the section from Question 1 to Question 2
        start_pos = q1_match.end()
        q2_match = re.search(r'(?:\n|^)\s*(Question\s*2|SECTION\s*[-–]?\s*B)', text[start_pos:], re.IGNORECASE)
        
        if q2_match:
            q1_section = text[start_pos:start_pos + q2_match.start()]
        else:
            # If no Question 2, take pages worth of content
            q1_section = text[start_pos:start_pos + 20000]  # Increased limit
        
        print(f"  Question 1 section length: {len(q1_section)} characters")
        print("  Q1 section preview:", q1_section[:800])

        # Chem-style: [1](a) marker, options inline or multiline
        chem_style = list(re.finditer(
            r'([^\n]+?\[\d+\]\([a-z]\))\s*((?:[^\n]*[a-d]\)[^\n]*){2,4})',
            q1_section,
            re.IGNORECASE
        ))
        if chem_style:
            print(f"  Found {len(chem_style)} Chem-style MCQs")
            for m in chem_style:
                question_text = m.group(1)
                options_text = m.group(2)
                part_letter = re.search(r'\([a-z]\)', question_text, re.IGNORECASE)
                part_num = part_letter.group(0) if part_letter else ""
                result = self.extract_mcq_parts(question_text + "\n" + options_text, part_num, solutions)
                if result:
                    print(f"    Extracted: {result['question'][:60]}... Options: {result['options']}")
                    mcqs.append(result)
            return mcqs

        # Fallback: split by [1](a), [1](b), etc.
        chem_parts = re.split(r'\[\d+\]\([a-z]\)', q1_section)
        for idx, part in enumerate(chem_parts[1:], 1):
            # Try to extract question and options from part
            result = self.extract_mcq_parts(part, f"(a)", solutions)
            if result:
                print(f"    Extracted: {result['question'][:60]}... Options: {result['options']}")
                mcqs.append(result)

        # Bio-style: (i) at line start, options multiline
        bio_style = list(re.finditer(
            r'(?m)^\s*\((i{1,3}|iv|v|vi{0,3}|ix|x|xi{1,3}|xiv|xv)\)\s*(.*?)\n((?:\s*\([a-d]\)\s*.*(?:\n|$)){2,4})',
            q1_section,
            re.IGNORECASE
        ))
        if bio_style:
            print(f"  Found {len(bio_style)} Bio-style MCQs")
            for m in bio_style:
                part_num = f"({m.group(1)})"
                question_text = m.group(2)
                options_text = m.group(3)
                result = self.extract_mcq_parts(question_text + "\n" + options_text, part_num, solutions)
                if result:
                    print(f"    Extracted: {result['question'][:60]}... Options: {result['options']}")
                    mcqs.append(result)
            return mcqs

        # Fallback: old splitting
        question_starts = list(re.finditer(
            r'(?m)^\s*(\(?[ivx]+\)|\(?[a-z]\)|\d+[\).])\s+',
            q1_section,
            re.IGNORECASE
        ))
        
        if question_starts:
            print(f"  Found {len(question_starts)} potential MCQ parts")
            for idx, m in enumerate(question_starts):
                part_num = m.group(1).strip()
                start = m.start()
                end = question_starts[idx + 1].start() if idx + 1 < len(question_starts) else len(q1_section)
                content = q1_section[start:end]
                
                result = self.extract_mcq_parts(content, part_num, solutions)
                if result:
                    mcqs.append(result)
        else:
            # Fallback: split by roman numerals at line start
            roman_pattern = r'(?m)^\s*((?:\(?)(?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv)(?:\)?))\s+'
            parts = re.split(roman_pattern, q1_section, flags=re.IGNORECASE)
            print(f"  Found {len(parts)//2} potential MCQ parts")
            
            for i in range(1, len(parts), 2):
                part_num = parts[i].strip()
                content = parts[i + 1] if i + 1 < len(parts) else ""
                
                if not content.strip():
                    continue
                
                result = self.extract_mcq_parts(content, part_num, solutions)
                if result:
                    mcqs.append(result)
        
        return mcqs

    def extract_mcq_parts(self, content, part_num, solutions):
        """Extract question text and options from MCQ content"""
        content = content.strip()
        
        # Remove leading question label (a), i), 1), etc.
        content = re.sub(r'^\s*(?:\(?[a-z]\)|\(?[ivx]+\)|\d+[\).])\s+', '', content, flags=re.IGNORECASE)
        
        # Find options (handles inline or multiline a) b) c) d))
        option_pattern = re.compile(
            r'(?i)(?:^|[\s])[\(\[\{]?\s*([a-d])\s*[\)\]\}]?\s+(.*?)(?=(?:^|[\s])[\(\[\{]?\s*[a-d]\s*[\)\]\}]?\s+|$)',
            re.DOTALL | re.MULTILINE
        )
        
        options = {'a': '', 'b': '', 'c': '', 'd': ''}
        option_matches = list(option_pattern.finditer(content))
        
        if option_matches:
            first_opt_start = option_matches[0].start()
            question_text = content[:first_opt_start].strip()
        else:
            question_text = content.strip()
        
        # Clean question text
        question_text = re.sub(r'\[\d+\]\s*\([a-z]\)\s*$', '', question_text, flags=re.IGNORECASE)
        question_text = re.sub(r'\[\d+\]', '', question_text)
        question_text = ' '.join(question_text.split())
        
        for m in option_matches:
            letter = m.group(1).lower()
            opt_text = ' '.join(m.group(2).split())
            if len(opt_text) > 300:
                opt_text = opt_text[:300] + "..."
            options[letter] = opt_text
        
        part_key = part_num.lower().strip()
        correct_answer = solutions.get(part_key, "")
        
        valid_options = sum(1 for v in options.values() if len(v) > 0)
        if question_text and len(question_text) > 10 and valid_options >= 3:
            return {
                'part': part_num,
                'question': question_text,
                'options': options,
                'correct_answer': correct_answer
            }
        
        return None
    
    def get_new_pdfs(self):
        """Get list of PDFs that haven't been parsed yet"""
        all_pdfs = list(Path(self.pdf_folder).glob("*.pdf"))
        new_pdfs = []
        
        for pdf_path in all_pdfs:
            pdf_name = pdf_path.name
            pdf_modified = os.path.getmtime(pdf_path)
            
            # Check if PDF is new or modified
            if pdf_name not in self.parsed_pdfs or self.parsed_pdfs[pdf_name] < pdf_modified:
                new_pdfs.append(pdf_path)
        
        return new_pdfs
    
    def process_pdfs(self):
        """Process new PDFs and update CSV"""
        new_pdfs = self.get_new_pdfs()
        
        if not new_pdfs:
            print("No new PDFs to process.")
            return
        
        print(f"Found {len(new_pdfs)} new PDF(s) to process...\n")
        
        # Check if CSV exists to determine if we need headers
        csv_exists = os.path.exists(self.output_csv)
        
        # Open CSV in append mode
        with open(self.output_csv, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Subject', 'Question_No', 'Question', 'Option_A', 'Option_B', 'Option_C', 'Option_D', 'Correct_Answer']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header only if file is new
            if not csv_exists:
                writer.writeheader()
            
            # Process each new PDF
            for pdf_path in new_pdfs:
                print(f"Processing: {pdf_path.name}")
                
                # Extract text
                text = self.extract_text_from_pdf(pdf_path)
                if not text or len(text) < 100:
                    print(f"  Could not extract sufficient text from {pdf_path.name}")
                    continue
                
                # Extract subject
                subject = self.extract_subject(text)
                print(f"  Subject: {subject}")
                
                # Extract solutions
                solutions = self.extract_solutions(text)
                if solutions:
                    print(f"  Found solutions for {len(solutions)} questions")
                else:
                    print("  No solutions found in PDF")
                
                # Parse Question 1 MCQs
                mcqs = self.parse_question_1_mcqs(text, solutions)
                
                print(f"  Found {len(mcqs)} MCQs in Question 1")
                
                # Write to CSV
                for mcq in mcqs:
                    writer.writerow({
                        'Subject': subject,
                        'Question_No': f"Q1-{mcq['part']}",
                        'Question': mcq['question'],
                        'Option_A': mcq['options']['a'],
                        'Option_B': mcq['options']['b'],
                        'Option_C': mcq['options']['c'],
                        'Option_D': mcq['options']['d'],
                        'Correct_Answer': mcq['correct_answer']
                    })
                
                # Update tracking
                self.parsed_pdfs[pdf_path.name] = os.path.getmtime(pdf_path)
                
                print()
        
        # Save tracking file
        self.save_tracking()
        print(f"Processing complete! Results saved to {self.output_csv}")
        print(f"Tracking file updated: {self.tracking_file}")

def main():
    # Configuration
    PDF_FOLDER = r"D:\Suganthi\Projects\MCQ-Test-App\MCQ Extractor\PDF_FOLDER"
    OUTPUT_CSV = r"D:\Suganthi\Projects\MCQ-Test-App\MCQ Extractor\mcq_questions.csv"
    TRACKING_FILE = r"D:\Suganthi\Projects\MCQ-Test-App\MCQ Extractor\parsed_pdfs.json"
    
    # Create parser instance
    parser = PDFMCQParser(PDF_FOLDER, OUTPUT_CSV, TRACKING_FILE)
    
    # Process PDFs
    parser.process_pdfs()

if __name__ == "__main__":
    main()
