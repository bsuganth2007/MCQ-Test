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
            # Convert all PDF pages to images
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
        # Look for solution section - match 'solution', 'solutions', 'answer', or 'answers' as section headers
        match = re.search(r'\b(solutions?|answers?)\b[\s:.-]*', text, re.IGNORECASE)
        solution_section = None
        if match:
            start = match.start()
            # Try to end at next section header or question
            q2_match = re.search(r'(?:Question\s*2|SECTION\s*B|SECTION\s*II|PART\s*B)', text[start:], re.IGNORECASE)
            if q2_match:
                solution_section = text[start:start + q2_match.start()]
            else:
                solution_section = text[start:start + 15000]  # Extended for solutions
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
        """Parse Section 1, Section A, or Question 1 MCQs from the PDF text"""
        mcqs = []
        # Try multiple patterns for the MCQ section header
        section_patterns = [
            r'Section\s*1',
            r'Section\s*A',
            r'Question\s*1',
            r'\(Attempt all questions from this Section\.\)',
            r'40\s*marks'
        ]
        section_match = None
        for pattern in section_patterns:
            section_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if section_match:
                break
        if not section_match:
            print("  Could not find Section 1, Section A, or Question 1 header")
            return mcqs
        # Check for 'Choose', 'Correct', or 'Options' in the next 1-2 sentences after the header
        start_pos = section_match.end()
        # Look ahead 10 lines after the section header for MCQ keywords
        lines_after = text[start_pos:].splitlines()
        lookahead_text = '\n'.join(lines_after[:10])
        print("\n--- Text after section header (10 lines) ---\n")
        print(lookahead_text)
        print("\n--- End of lookahead text ---\n")
        if not re.search(r'(Choose|Correct|Options|Select|Right)', lookahead_text, re.IGNORECASE):
            print("  Section header found, but no MCQ keywords ('Choose', 'Correct', 'Options', 'Select', 'Right') in next 10 lines.")
            return mcqs
        # Look for next section/question header
        next_section_match = re.search(r'^(\s*Section\s*[2B]|\s*Question\s*2)', text[start_pos:], re.IGNORECASE | re.MULTILINE)
        if next_section_match:
            section_text = text[start_pos:start_pos + next_section_match.start()]
        else:
            section_text = text[start_pos:]
        print("\n--- Extracted MCQ Section (first 500 chars) ---\n")
        print(section_text[:500])
        print("\n--- End of MCQ Section ---\n")
        print(f"  MCQ section length: {len(section_text)} characters")
        # Split by roman numerals - match i), ii), iii), etc.
        roman_pattern = r'^\s*\(\s*(i{1,3}|iv|v|vi{0,3}|ix|x{1,3}|xi{1,3}|xiv|xv)\s*\)'
        parts = re.split(roman_pattern, section_text, flags=re.IGNORECASE | re.MULTILINE)
        print(f"  Found {len(parts)//2} potential MCQ parts")
        print("\n--- Debug: Parts after roman numeral split ---")
        for idx, part in enumerate(parts):
            print(f"Part {idx}: {repr(part[:200])}")
        print("--- End of parts debug ---\n")
        # Process parts in pairs (roman numeral, content)
        for i in range(1, len(parts), 2):
            if i >= len(parts):
                break
            part_num = parts[i].strip()
            content = parts[i + 1] if i + 1 < len(parts) else ""
            if not content.strip():
                continue
            # Extract question and options
            result = self.extract_mcq_parts(content, part_num, solutions)
            if result:
                mcqs.append(result)
        return mcqs
    
    def extract_mcq_parts(self, content, part_num, solutions):
        """Extract question text and options from MCQ content"""
        # Clean up content
        content = content.strip()
        
        # Find where options start - look for pattern (a), (b), (c), (d)
        # Also handle OCR errors like (a| or {a) etc.
        option_start = re.search(r'\n\s*[\(\[\{]a[\)\]\}]', content, re.IGNORECASE)
        if option_start:
            question_block = content[:option_start.start()].strip()
        else:
            lines = content.split('\n')
            question_lines = []
            for line in lines:
                if re.match(r'^\s*[\(\[\{][a-d][\)\]\}]', line, re.IGNORECASE):
                    break
                question_lines.append(line.strip())
            question_block = ' '.join(question_lines).strip()

        # Detect and preserve matrix notation in the question text
        matrix_patterns = [
            r'(\[\[.*?\]\])',  # [[...]]
            r'(⎡[\s\S]*?⎤)',    # Unicode matrix brackets
            r'(\\begin\{matrix\}[\s\S]*?\\end\{matrix\})',  # LaTeX
            r'(matrix\s*\n?(?:[\d\s,;\-]+\n?)+)'  # 'matrix' followed by numbers
        ]
        matrix_found = None
        for pat in matrix_patterns:
            m = re.search(pat, question_block, re.IGNORECASE)
            if m:
                matrix_found = m.group(1)
                break
        if matrix_found:
            question_text = question_block.replace(matrix_found, f"[MATRIX]{matrix_found}[/MATRIX]")
        else:
            question_text = question_block
        question_text = ' '.join(question_text.split())
        
        # Extract options - match all lines like (a) text, (b) text, etc.
        options = {'a': '', 'b': '', 'c': '', 'd': ''}
        option_matches = re.findall(r'^\s*\(([a-d])\)\s*(.*)', content, re.IGNORECASE | re.MULTILINE)
        for letter, opt_text in option_matches:
            letter = letter.lower()
            opt_text = ' '.join(opt_text.split())
            if len(opt_text) > 300:
                opt_text = opt_text[:300] + "..."
            options[letter] = opt_text
        
        # Get correct answer from solutions
        part_key = part_num.lower().strip()
        correct_answer = solutions.get(part_key, "")
        
        # Only return if we have a question and at least 3 options
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
            fieldnames = [
                'Subject',
                'Question no',
                'Question Description',
                'Option A',
                'Option B',
                'Option C',
                'Option D',
                'Correct Answer',
                'Source'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not csv_exists:
                writer.writeheader()
            for idx, pdf_path in enumerate(new_pdfs):
                print(f"Processing: {pdf_path.name}")
                text = self.extract_text_from_pdf(pdf_path)
                if idx == 0:
                    print("\n--- Extracted Text Start ---\n")
                    print(text[:3000])
                    print("\n--- Extracted Text End ---\n")
                if not text or len(text) < 100:
                    print(f"  Could not extract sufficient text from {pdf_path.name}")
                    continue
                subject = self.extract_subject(text)
                print(f"  Subject: {subject}")
                solutions = self.extract_solutions(text)
                if solutions:
                    print(f"  Found solutions for {len(solutions)} questions")
                else:
                    print("  No solutions found in PDF")
                mcqs = self.parse_question_1_mcqs(text, solutions)
                print(f"  Found {len(mcqs)} MCQs in Question 1")
                for mcq in mcqs:
                    writer.writerow({
                        'Subject': subject,
                        'Question no': f"Q1-{mcq['part']}",
                        'Question Description': mcq['question'],
                        'Option A': mcq['options']['a'],
                        'Option B': mcq['options']['b'],
                        'Option C': mcq['options']['c'],
                        'Option D': mcq['options']['d'],
                        'Correct Answer': mcq['correct_answer'],
                        'Source': pdf_path.name
                    })
                self.parsed_pdfs[pdf_path.name] = os.path.getmtime(pdf_path)
                print()
        # Save tracking file
        self.save_tracking()
        print(f"Processing complete! Results saved to {self.output_csv}")
        print(f"Tracking file updated: {self.tracking_file}")

def main():
    # Configuration
    PDF_FOLDER = r"D:/Suganthi/Projects/MCQ-Test-App/MCQ Extractor/PDF_FOLDER"  # Folder containing PDFs
    OUTPUT_CSV = r"D:/Suganthi/Projects/MCQ-Test-App/MCQ Extractor/mcq_questions.csv"
    TRACKING_FILE = r"D:/Suganthi/Projects/MCQ-Test-App/MCQ Extractor/parsed_pdfs.json"

    # Create parser instance
    parser = PDFMCQParser(PDF_FOLDER, OUTPUT_CSV, TRACKING_FILE)

    # Process PDFs
    parser.process_pdfs()

if __name__ == "__main__":
    main()
