import os
import json
import csv
import re
from pathlib import Path
from pypdf import PdfReader

try:
    import pdf2image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Roman numerals i–xv (longer alternatives MUST come before shorter ones)
ROMAN_RE = r'(?:xv|xiv|xiii|xii|xi|ix|viii|vii|vi|iv|iii|ii|x{1,3}|v|i)'

# Alphabet labels a–o (covers up to 15 MCQs)
ALPHA_RE = r'[a-o]'


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r'\s+', ' ', text).strip()


def normalize_roman(r: str) -> str:
    """Return canonical lowercase roman string ending with ')'.  e.g. 'ii)'"""
    return r.lower().strip().rstrip(')').strip() + ')'


def option_letter_to_word(letter: str) -> str:
    return f"Option {letter.upper()}"


# Mapping: alphabet question label → roman numeral solution label
# Used when a paper numbers questions (a)-(o) but solutions (i)-(xv)
_ALPHA_TO_ROMAN = {
    'a': 'i)',  'b': 'ii)',  'c': 'iii)', 'd': 'iv)',  'e': 'v)',
    'f': 'vi)', 'g': 'vii)', 'h': 'viii)','i': 'ix)',  'j': 'x)',
    'k': 'xi)', 'l': 'xii)', 'm': 'xiii)','n': 'xiv)', 'o': 'xv)',
}

def lookup_solution(label: str, solutions: dict) -> str:
    """
    Look up correct answer for a question label.
    Tries the label directly (e.g. 'a)'), then its roman equivalent
    (e.g. 'i)') to handle papers where questions use alphabets but
    solutions use roman numerals.
    """
    direct = solutions.get(label + ')', '')
    if direct:
        return direct
    roman = _ALPHA_TO_ROMAN.get(label.lower(), '')
    return solutions.get(roman, '')


_ARTIFACT_RE = re.compile(
    r'^(?:Page \d+ of \d+'
    r'|ICSE\b'
    r'|Sample Question'
    r'|www\.'
    r'|©'
    r'|\d{4}\s+Exam'
    r'|(?:Mathematics|Maths|Physics|Chemistry|Biology|English|Science|History|Geography|Economics|Computer)\s*$'
    r')',
    re.IGNORECASE
)

def remove_artifacts(lines: list) -> list:
    return [l for l in lines if not _ARTIFACT_RE.match(l)]


# ─────────────────────────────────────────────────────────────────────────────
#  OPTION PARSER  — handles BOTH layout styles
#
#  LIST layout (one per line):
#      (a) text one
#      (b) text two
#      (c) text three
#      (d) text four
#
#  TWO-COLUMN layout (two per line, separated by 2+ spaces):
#      a) text one    b) text two
#      c) text three  d) text four
#
#  Recognised delimiters: (a)  a)  a.  [a]  {a}
# ─────────────────────────────────────────────────────────────────────────────

def parse_options(block: str) -> dict:
    opts = {'a': '', 'b': '', 'c': '', 'd': ''}

    # ── Pass 1: two-column scan (each line) ───────────────────────────────────
    # Two-column: "a) text  b) text"  or  "a)text b)text"
    # The key signal is the presence of both a) and b) on the same line.
    # Allow zero or more spaces after the delimiter.
    two_col_ab = re.compile(
        r'^[(\[{]?a[)\]}.]\s*(.+?)\s+[(\[{]?b[)\]}.]\s*(.+)$',
        re.IGNORECASE
    )
    two_col_cd = re.compile(
        r'^[(\[{]?c[)\]}.]\s*(.+?)\s+[(\[{]?d[)\]}.]\s*(.+)$',
        re.IGNORECASE
    )

    for line in block.split('\n'):
        line = line.strip()
        m = two_col_ab.match(line)
        if m:
            opts['a'] = clean(m.group(1))
            opts['b'] = clean(m.group(2))
            continue
        m = two_col_cd.match(line)
        if m:
            opts['c'] = clean(m.group(1))
            opts['d'] = clean(m.group(2))
            continue

    if opts['a'] and opts['c']:          # both rows found → done
        return opts

    # ── Pass 2: list layout via sequential split ──────────────────────────────
    # Split the block at every option delimiter
    splitter = re.compile(
        r'(?:^|\n)\s*[(\[{]?([a-d])[)\]}.]\s+',
        re.IGNORECASE | re.MULTILINE
    )
    segments = splitter.split(block)
    # segments = [pre_text, 'a', text_a, 'b', text_b, …]
    i = 1
    while i < len(segments) - 1:
        letter  = segments[i].lower()
        content = segments[i + 1] if i + 1 < len(segments) else ''
        # Trim at the next option delimiter to avoid bleed-over
        content = re.split(r'\n\s*[(\[{]?[a-d][)\]}.]\s', content)[0]
        if letter in opts and not opts[letter]:
            opts[letter] = clean(content)
        i += 2

    return opts


# ─────────────────────────────────────────────────────────────────────────────
#  QUESTION-TYPE DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

def detect_question_type(q1_section: str) -> str:
    """
    Returns 'roman' (Type 1) or 'alpha' (Type 2).

    Type 1 – questions numbered with roman numerals:  i)  (i)  ii)  …
    Type 2 – questions numbered with alphabets:  [1](a)  (a)  (b)  …
    """
    roman_hits = len(re.findall(
        rf'(?:^|\n)\s*\(?({ROMAN_RE})\s*[).]',
        q1_section, re.IGNORECASE | re.MULTILINE
    ))
    # Type-2 marker is either [1](letter) OR a capital-letter question after (letter)
    alpha_hits = len(re.findall(
        rf'(?:\[1\]\s*\(({ALPHA_RE})\))',
        q1_section, re.IGNORECASE
    ))
    # Give a small bonus to alpha if the [1](x) marker appears at all
    if alpha_hits > 0:
        alpha_hits += 3

    return 'roman' if roman_hits > alpha_hits else 'alpha'


# ─────────────────────────────────────────────────────────────────────────────
#  TYPE 1  –  Roman numeral questions
#  Structure:  (i) Question text\n(a) opt\n(b) opt\n(c) opt\n(d) opt
# ─────────────────────────────────────────────────────────────────────────────

def _split_at_first_option(content: str):
    """Return (question_text, options_block) split at first option line."""
    opt_start = re.search(
        r'(?:^|\n)\s*[(\[{]?[a-d][)\]}.]\s',
        content, re.MULTILINE
    )
    if opt_start:
        return content[:opt_start.start()].strip(), content[opt_start.start():]
    return content.strip(), ''


def parse_type1(q1_section: str, solutions: dict) -> list:
    """
    Split by roman-numeral labels and extract each MCQ.
    Accepts:  i)  (i)  i.   at the start of a line.
    """
    mcqs = []

    splitter = re.compile(
        rf'(?:^|\n)\s*\(?({ROMAN_RE})\s*[).]',
        re.IGNORECASE | re.MULTILINE
    )
    parts = splitter.split(q1_section)
    # parts = [preamble, 'i', body_i, 'ii', body_ii, …]

    for i in range(1, len(parts), 2):
        label   = parts[i].strip().lower()
        content = (parts[i + 1] if i + 1 < len(parts) else '').strip()

        question_raw, options_block = _split_at_first_option(content)
        question = clean(question_raw)
        options  = parse_options(options_block) if options_block else parse_options(content)
        valid    = sum(1 for v in options.values() if v)

        if question and valid >= 3:
            mcqs.append({
                'part'          : f"({label})",
                'question'      : question,
                'options'       : options,
                'correct_answer': solutions.get(normalize_roman(label), ''),
            })

    return mcqs


# ─────────────────────────────────────────────────────────────────────────────
#  TYPE 2  –  Alphabet questions  (a) … (o)
#  Two known sub-layouts:
#
#  Layout 2A  [reversed / Chemistry-style]:
#      options come BEFORE the [1](letter) marker in the PDF stream
#      i.e.  a) opt  b) opt  \n  c) opt  d) opt  \n  question text [1](a)
#
#  Layout 2B  [normal]:
#      (a) question text \n a) opt \n b) opt \n …
# ─────────────────────────────────────────────────────────────────────────────

def parse_type2(q1_section: str, solutions: dict) -> list:
    mcqs = []

    # ── Try Layout 2A: split by [1](letter) markers ───────────────────────────
    marker_re = re.compile(r'\[1\]\s*\(([a-o])\)', re.IGNORECASE)
    parts = marker_re.split(q1_section)

    if len(parts) >= 3:
        # Layout 2A (reversed):
        #   PDF stream: options_of_Q(n) → question_fragment → [1](n) → remainder → options_of_Q(n+1) → …
        #   Solutions use roman numerals (i)-(xv); questions use alphabets (a)-(o).
        #   lookup_solution() handles both direct and alpha→roman fallback.
        for i in range(1, len(parts), 2):
            label  = parts[i].lower()
            before = parts[i - 1]
            after  = parts[i + 1] if i + 1 < len(parts) else ''

            # ── Options: last option block in 'before' ───────────────────────
            options = parse_options(before)

            # ── Question: tail of 'before' + head of 'after' ─────────────────
            before_lines = remove_artifacts(
                [l.strip() for l in before.split('\n') if l.strip()]
            )
            after_lines = remove_artifacts(
                [l.strip() for l in after.split('\n') if l.strip()]
            )

            # Tail of before = lines after the last option line
            last_opt = -1
            for idx, ln in enumerate(before_lines):
                if re.match(r'^[(\[{]?[a-d][)\]}.]\s*\S', ln, re.IGNORECASE):
                    last_opt = idx
            before_tail = before_lines[last_opt + 1:] if last_opt >= 0 else []

            # Head of after = lines before the first option line of Q(n+1)
            after_head, _ = _split_lines_at_option(after_lines)

            # Combine fragments (question text may be split across the marker)
            q_parts = before_tail + [t for t in after_head
                                     if t not in before_tail and len(t) > 1]
            question = clean(' '.join(q_parts))

            # ── Fallback options: try full 'after' block ────────────────────
            if not any(options.values()):
                options = parse_options(after)

            valid = sum(1 for v in options.values() if v)
            if question and valid >= 3:
                mcqs.append({
                    'part'          : f"({label})",
                    'question'      : question,
                    'options'       : options,
                    'correct_answer': lookup_solution(label, solutions),
                })
        return mcqs

    # ── Layout 2B: normal (letter) at start of line ───────────────────────────
    fallback_re = re.compile(
        r'(?:^|\n)\s*\(([a-o])\)\s+',
        re.MULTILINE | re.IGNORECASE
    )
    parts2 = fallback_re.split(q1_section)

    for i in range(1, len(parts2), 2):
        label   = parts2[i].lower()
        content = (parts2[i + 1] if i + 1 < len(parts2) else '').strip()
        lines   = remove_artifacts([l.strip() for l in content.split('\n') if l.strip()])
        q_lines, opt_lines = _split_lines_at_option(lines)
        question = clean(' '.join(q_lines))
        options  = parse_options('\n'.join(opt_lines)) if opt_lines else parse_options(content)
        valid    = sum(1 for v in options.values() if v)
        if question and valid >= 3:
            mcqs.append({
                'part'          : f"({label})",
                'question'      : question,
                'options'       : options,
                'correct_answer': lookup_solution(label, solutions),
            })

    return mcqs


def _split_lines_at_option(lines: list):
    """Split a list of lines into (question_lines, option_lines)."""
    # Match lines that START with an option delimiter (with or without space after)
    opt_re = re.compile(r'^[(\[{]?[a-d][)\]}.]\s*\S', re.IGNORECASE)
    for idx, ln in enumerate(lines):
        if opt_re.match(ln):
            return lines[:idx], lines[idx:]
    return lines, []


# ─────────────────────────────────────────────────────────────────────────────
#  SOLUTION EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

def extract_solutions(text: str) -> dict:
    """
    Locate the Solution section and extract Q1 correct answers.
    Returns dict keyed by roman numeral: {'i)': 'Option A', 'ii)': 'Option B', …}

    Handles two known formats:

    Format A — answer and counter on consecutive lines (Chemistry 2026 style):
        (a) II A group and 5th period
        (i)
        (d) Beryllium
        (ii)
        ...

    Format B — answer and counter on the same line:
        (i) (a) text  or  (i) Option (a) is correct
    """
    solutions = {}

    # The solution section is identified by the SECOND occurrence of
    # "Section A\n1. Question 1" in the document — the first is the
    # question paper, the second is the answer key.
    # Fall back to any standalone "Solution" heading if that pattern is absent.
    q1_ans_marker = re.compile(
        r'Section A\s*\n\s*1\.\s*Question\s*1\b.*?correct answer',
        re.IGNORECASE | re.DOTALL
    )
    all_markers = list(q1_ans_marker.finditer(text))

    if len(all_markers) >= 2:
        # Second occurrence = solution section
        sol_start = all_markers[1].start()
    else:
        # Fallback: lone "Solution" heading on its own line
        sol_match = re.search(r'(?:^|\n)Solution\s*\n', text, re.IGNORECASE)
        if not sol_match:
            return solutions
        sol_start = sol_match.start()

    sol_text = text[sol_start:]

    # Stop just after the (xv) counter — that marks the end of Q1 answers.
    # We do NOT stop at "2. Question 2" because on page 8 the Q2 header appears
    # BEFORE the (xi)–(xv) answers due to page-break layout.
    stop = re.search(r'\(\s*xv\s*\)\s*\n', sol_text, re.IGNORECASE)
    if stop:
        sol_text = sol_text[:stop.end() + 300]   # keep a little context after (xv)

    # ── Format A: (answer_text) ... (roman_counter) interleaved pattern ───────
    #
    # Each Q1 answer block in the solution looks like:
    #   (a) answer text          ← ANS line  (option letter + answer value)
    #   Explanation:
    #   ... explanation body ... (may span multiple lines, including equations)
    #   (i)                      ← CTR line  (roman numeral, alone on its line)
    #   (d) next answer
    #   ...
    #   (ii)
    #
    # Mapping rule: each CTR line belongs to the LAST ANS line that precedes it.

    lines = [l.strip() for l in sol_text.split('\n') if l.strip()]

    answer_line_re  = re.compile(r'^\(([a-d])\)\s+(.+)$',    re.IGNORECASE)
    counter_line_re = re.compile(rf'^\(({ROMAN_RE})\)$',      re.IGNORECASE)

    # Collect (line_index, option_letter) for every ANS line
    ans_lines = [
        (idx, answer_line_re.match(ln).group(1).lower())
        for idx, ln in enumerate(lines)
        if answer_line_re.match(ln)
    ]
    # Collect (line_index, roman) for every CTR line
    ctr_lines = [
        (idx, counter_line_re.match(ln).group(1).lower())
        for idx, ln in enumerate(lines)
        if counter_line_re.match(ln)
    ]

    # For each CTR, pair it with the last ANS that appears before it
    for ctr_idx, roman in ctr_lines:
        preceding = [(ai, a) for ai, a in ans_lines if ai < ctr_idx]
        if not preceding:
            continue
        _, option_letter = preceding[-1]      # last ANS before this CTR
        key = normalize_roman(roman)
        # Only store Q1 answers (stop when we hit Q2's (i) counter again)
        if key not in solutions:
            solutions[key] = option_letter_to_word(option_letter)

    # ── Format B: same-line patterns (fallback if Format A found nothing) ─────
    if not solutions:
        # (roman) (option_letter) text   or   (roman) Option (option_letter)
        patB1 = re.compile(
            rf'\(\s*({ROMAN_RE})\s*\)\s*\(?([a-d])\)?(?:\s+is\s+correct)?',
            re.IGNORECASE
        )
        patB2 = re.compile(
            rf'\(\s*({ROMAN_RE})\s*\)\s*Option\s*\(?([a-d])\)?',
            re.IGNORECASE
        )
        for pat in (patB1, patB2):
            for m in pat.finditer(sol_text):
                key = normalize_roman(m.group(1))
                if key not in solutions:
                    solutions[key] = option_letter_to_word(m.group(2))

    return solutions


# ─────────────────────────────────────────────────────────────────────────────
#  SUBJECT EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

_SUBJECTS = [
    'Mathematics', 'Maths', 'Physics', 'Chemistry',
    'Biology', 'English', 'Science', 'History',
    'Geography', 'Economics', 'Computer',
]

def extract_subject(text: str) -> str:
    # Search first 3000 chars (covers title pages that appear after instructions)
    haystack = text[:3000]
    for s in _SUBJECTS:
        if re.search(rf'\b{re.escape(s)}\b', haystack, re.IGNORECASE):
            return 'Mathematics' if s.lower() == 'maths' else s.capitalize()
    return 'Unknown'


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN PARSER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class PDFMCQParser:

    FIELDNAMES = [
        'Subject', 'Question',
        'Option A', 'Option B', 'Option C', 'Option D',
        'Correct_Answer',
    ]

    def __init__(self, pdf_folder, output_csv, tracking_file='parsed_pdfs.json'):
        self.pdf_folder    = pdf_folder
        self.output_csv    = output_csv
        self.tracking_file = tracking_file
        self.parsed_pdfs   = self._load_tracking()

    # ── Tracking ──────────────────────────────────────────────────────────────

    def _load_tracking(self):
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file) as f:
                return json.load(f)
        return {}

    def _save_tracking(self):
        with open(self.tracking_file, 'w') as f:
            json.dump(self.parsed_pdfs, f, indent=2)

    # ── Text extraction ───────────────────────────────────────────────────────

    def extract_text(self, pdf_path: str) -> str:
        try:
            reader = PdfReader(pdf_path)
            text   = '\n'.join(p.extract_text() or '' for p in reader.pages)
            if len(text.strip()) > 100:
                return text
            if OCR_AVAILABLE:
                print('  Image-based PDF – running OCR …')
                return self._ocr(pdf_path)
            print('  WARNING: minimal text and OCR not available.')
            return text
        except Exception as e:
            print(f'  Error reading {pdf_path}: {e}')
            return ''

    def _ocr(self, pdf_path: str) -> str:
        images = pdf2image.convert_from_path(pdf_path)
        pages  = []
        for i, img in enumerate(images, 1):
            print(f'    OCR page {i}/{len(images)} …')
            pages.append(pytesseract.image_to_string(img))
        return '\n'.join(pages)

    # ── Q1 isolation ──────────────────────────────────────────────────────────

    def _isolate_q1(self, text: str) -> str:
        """Return the Question 1 MCQ section text."""
        q1_hdr = re.search(
            r'Question\s*1\s+(?:Choose|Select).*?(?:options?|given)\s*:?\s*(?:\[\d+\])?',
            text, re.IGNORECASE | re.DOTALL
        )
        if not q1_hdr:
            q1_hdr = re.search(r'\b1\.\s*Question\s*1\b', text, re.IGNORECASE)
        if not q1_hdr:
            q1_hdr = re.search(r'Question\s*1\b', text, re.IGNORECASE)
        if not q1_hdr:
            return ''

        start = q1_hdr.end()
        # End at "2. Question 2" or "Question 2"
        q2 = re.search(r'\n\s*(?:\d+\.\s*)?Question\s*2\b', text[start:], re.IGNORECASE)
        end = start + q2.start() if q2 else start + 10000
        return text[start:end]

    # ── Public parse API ──────────────────────────────────────────────────────

    def parse_pdf(self, pdf_path: str) -> list:
        """Parse a single PDF and return list of MCQ dicts. Attempts OCR fallback for Biology/Science/Unknown if needed."""
        print(f'\nProcessing: {Path(pdf_path).name}')

        text = self.extract_text(pdf_path)
        if not text or len(text) < 100:
            print('  Could not extract sufficient text.')
            return []

        subject   = extract_subject(text)
        solutions = extract_solutions(text)
        print(f'  Subject   : {subject}')
        print(f'  Solutions : {len(solutions)} found  {dict(list(solutions.items())[:6])}')

        q1_section = self._isolate_q1(text)
        if not q1_section:
            print('  Could not isolate Question 1.')
            return []
        print(f'  Q1 section: {len(q1_section)} chars')

        q_type = detect_question_type(q1_section)
        print(f'  Format    : {"Type 1 – roman numerals" if q_type == "roman" else "Type 2 – alphabets"}')

        mcqs = parse_type1(q1_section, solutions) if q_type == 'roman' \
               else parse_type2(q1_section, solutions)

        # Fallback: If subject is Biology/Science/Unknown and MCQs < 10, try OCR if not already used
        if (subject.lower() in {"biology", "science", "unknown"}) and len(mcqs) < 10 and OCR_AVAILABLE:
            print(f'  Few MCQs ({len(mcqs)}) found for {subject}. Retrying with OCR...')
            ocr_text = self._ocr(pdf_path)
            ocr_solutions = extract_solutions(ocr_text)
            ocr_q1_section = self._isolate_q1(ocr_text)
            if ocr_q1_section:
                ocr_q_type = detect_question_type(ocr_q1_section)
                print(f'  OCR Q1 section: {len(ocr_q1_section)} chars, Format: {"Type 1 – roman numerals" if ocr_q_type == "roman" else "Type 2 – alphabets"}')
                ocr_mcqs = parse_type1(ocr_q1_section, ocr_solutions) if ocr_q_type == 'roman' else parse_type2(ocr_q1_section, ocr_solutions)
                if len(ocr_mcqs) > len(mcqs):
                    print(f'  OCR improved MCQ extraction: {len(ocr_mcqs)} MCQs')
                    mcqs = ocr_mcqs

        print(f'  Extracted : {len(mcqs)} MCQs')
        for m in mcqs:
            m['subject'] = subject
        return mcqs

    # ── Batch CSV processing ──────────────────────────────────────────────────

    def process_pdfs(self):
        """Process all new/updated PDFs in pdf_folder and append to CSV."""
        all_pdfs = list(Path(self.pdf_folder).glob('*.pdf'))
        new_pdfs = [
            p for p in all_pdfs
            if p.name not in self.parsed_pdfs
            or self.parsed_pdfs[p.name] < os.path.getmtime(p)
        ]

        if not new_pdfs:
            print('No new PDFs to process.')
            return

        print(f'Found {len(new_pdfs)} new PDF(s) to process …')

        csv_exists = os.path.exists(self.output_csv)
        with open(self.output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            if not csv_exists:
                writer.writeheader()

            for pdf_path in new_pdfs:
                mcqs = self.parse_pdf(str(pdf_path))
                for mcq in mcqs:
                    writer.writerow({
                        'Subject'       : mcq['subject'],
                        'Question'      : mcq['question'],
                        'Option A'      : mcq['options']['a'],
                        'Option B'      : mcq['options']['b'],
                        'Option C'      : mcq['options']['c'],
                        'Option D'      : mcq['options']['d'],
                        'Correct_Answer': mcq['correct_answer'],
                    })
                self.parsed_pdfs[pdf_path.name] = os.path.getmtime(pdf_path)

        self._save_tracking()
        print(f'\nDone. Results saved to: {self.output_csv}')
        print(f'Tracking updated      : {self.tracking_file}')


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    PDF_FOLDER    = r"D:\Suganthi\Projects\MCQ-Test-App\MCQ Extractor\PDF_FOLDER"
    OUTPUT_CSV    = r"D:\Suganthi\Projects\MCQ-Test-App\MCQ Extractor\mcq_questions.csv"
    TRACKING_FILE = r"D:\Suganthi\Projects\MCQ-Test-App\MCQ Extractor\parsed_pdfs.json"

    os.makedirs(Path(OUTPUT_CSV).parent, exist_ok=True)

    parser = PDFMCQParser(PDF_FOLDER, OUTPUT_CSV, TRACKING_FILE)
    parser.process_pdfs()


if __name__ == '__main__':
    main()
