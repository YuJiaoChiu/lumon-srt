import re
import json
import logging
from collections import Counter
from typing import Dict, Tuple, List, Any
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CorrectionEngine:
    """
    SRT subtitle correction engine based on sub2024_9.py logic.
    This class handles the core correction functionality with optimizations for web usage.
    """

    def __init__(self, correction_dict_file: str = "terms.json", protection_dict_file: str = "保护terms.json"):
        """
        Initialize the correction engine with dictionary files.

        Args:
            correction_dict_file (str): Path to the correction dictionary JSON file
            protection_dict_file (str): Path to the protection dictionary JSON file
        """
        self.correction_dict_file = correction_dict_file
        self.protection_dict_file = protection_dict_file
        self.correction_dict = {}
        self.protection_dict = {}
        self.load_dictionaries()

    def load_dictionaries(self):
        """Load both correction and protection dictionaries from files."""
        self.correction_dict = self.load_dictionary(self.correction_dict_file)
        self.protection_dict = self.load_dictionary(self.protection_dict_file)
        logger.info(f"Loaded correction dictionary with {len(self.correction_dict)} entries")
        logger.info(f"Loaded protection dictionary with {len(self.protection_dict)} entries")

    def load_dictionary(self, filename: str) -> Dict[str, str]:
        """
        Load a dictionary from a JSON file.

        Args:
            filename (str): Path to the dictionary file

        Returns:
            Dict[str, str]: The loaded dictionary
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Dictionary file {filename} not found. Creating empty dictionary.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {filename}. Creating empty dictionary.")
            return {}

    def save_dictionary(self, dictionary: Dict[str, str], filename: str) -> bool:
        """
        Save a dictionary to a JSON file.

        Args:
            dictionary (Dict[str, str]): The dictionary to save
            filename (str): Path to save the dictionary to

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(dictionary, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving dictionary to {filename}: {str(e)}")
            return False

    def update_correction_dict(self, new_dict: Dict[str, str]) -> bool:
        """
        Update the correction dictionary and save it to file.

        Args:
            new_dict (Dict[str, str]): The new dictionary

        Returns:
            bool: True if successful, False otherwise
        """
        self.correction_dict = new_dict
        return self.save_dictionary(self.correction_dict, self.correction_dict_file)

    def update_protection_dict(self, new_dict: Dict[str, str]) -> bool:
        """
        Update the protection dictionary and save it to file.

        Args:
            new_dict (Dict[str, str]): The new dictionary

        Returns:
            bool: True if successful, False otherwise
        """
        self.protection_dict = new_dict
        return self.save_dictionary(self.protection_dict, self.protection_dict_file)

    def should_correct(self, wrong: str, protected_words: Dict[str, str]) -> bool:
        """
        Determine if a term should be corrected based on protection dictionary.

        Args:
            wrong (str): The term to check
            protected_words (Dict[str, str]): Dictionary of protected terms

        Returns:
            bool: True if the term should be corrected, False otherwise
        """
        wrong_lower = wrong.lower()
        for protected in protected_words:
            protected_lower = protected.lower()
            if protected_lower in wrong_lower:
                if protected_lower != wrong_lower:
                    return True
                return False
            if wrong_lower in protected_lower:
                return False
        return True

    def validate_srt(self, text: str) -> bool:
        """
        Validate if the text is a properly formatted SRT file.

        Args:
            text (str): The SRT file content

        Returns:
            bool: True if valid SRT format, False otherwise
        """
        # Basic validation - check for timestamp format
        timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}')
        if not timestamp_pattern.search(text):
            logger.warning("No timestamp pattern found in file")
            return False
        return True

    def correct_subtitles(self, text: str, callback=None) -> Tuple[str, Dict[Tuple[str, str], int]]:
        """
        Correct subtitles based on correction and protection dictionaries.

        Args:
            text (str): The SRT file content
            callback (callable, optional): Callback function for progress updates

        Returns:
            Tuple[str, Dict[Tuple[str, str], int]]: (corrected_text, replacements_counter)
        """
        if not self.validate_srt(text):
            logger.warning("Invalid SRT format detected")
            return text, {}

        # Precompile patterns for better performance
        patterns = {}
        for wrong, correct in self.correction_dict.items():
            if self.should_correct(wrong, self.protection_dict):
                # Check if the term is an English word (contains only ASCII letters)
                is_english_word = all(c.isalpha() and ord(c) < 128 for c in wrong.strip())

                if is_english_word:
                    # For English words, add word boundary markers
                    pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
                else:
                    # For non-English terms (like Chinese), use simple pattern
                    pattern = re.compile(re.escape(wrong), re.IGNORECASE)

                patterns[wrong] = (pattern, correct)

        # Sort correction items by length (longest first) for proper matching
        sorted_correction_items = sorted(
            [(wrong, correct, pattern) for wrong, (pattern, correct) in patterns.items()],
            key=lambda x: len(x[0]),
            reverse=True
        )

        # Process in chunks for better performance and memory usage
        chunk_size = 1000  # Process 1000 lines at a time
        lines = text.split('\n')
        total_lines = len(lines)
        corrected_lines = []
        replacements = Counter()

        for chunk_start in range(0, total_lines, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_lines)
            chunk = lines[chunk_start:chunk_end]

            # Update progress
            if callback:
                callback(chunk_start / total_lines * 100)

            for i, line in enumerate(chunk):
                # Skip timestamp lines
                if '-->' in line:
                    corrected_lines.append(line)
                    continue

                # Skip lines that are just parenthetical comments
                if re.match(r'^\s*\([^)]*\)\s*$', line):
                    continue

                original_line = line
                replaced_positions = []  # Track replaced positions to avoid overlaps

                for wrong, correct, pattern in sorted_correction_items:
                    def replace_func(match):
                        start, end = match.span()
                        # Check if this position overlaps with any already replaced position
                        if any(start < pos[1] and end > pos[0] for pos in replaced_positions):
                            return match.group(0)  # If already replaced, return original text

                        replaced = correct if correct else ''
                        if match.group(0).isupper():
                            replaced = replaced.upper()
                        elif match.group(0).istitle():
                            replaced = replaced.capitalize()

                        # Record this position as replaced
                        replaced_positions.append((start, end))
                        return replaced

                    new_line, count = pattern.subn(replace_func, line)
                    if count > 0:
                        line = new_line
                        replacements[(wrong, correct)] += count

                corrected_lines.append(line)

        # Final progress update
        if callback:
            callback(100)

        return '\n'.join(corrected_lines), replacements

    def process_file(self, file_path: str, output_path: str = None, callback=None) -> Dict[str, Any]:
        """
        Process a single SRT file and save the corrected version.

        Args:
            file_path (str): Path to the SRT file
            output_path (str, optional): Path to save the corrected file
            callback (callable, optional): Callback function for progress updates

        Returns:
            Dict[str, Any]: Processing results including replacements
        """
        start_time = time.time()

        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Process the file
            corrected_content, replacements = self.correct_subtitles(content, callback)

            # Determine output path if not provided
            if not output_path:
                path = Path(file_path)
                output_path = path.with_name(f"{path.stem}_corrected{path.suffix}")

            # Save the corrected file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(corrected_content)

            elapsed_time = time.time() - start_time

            # Convert tuple keys to strings in replacements dictionary
            string_replacements = {}
            for key, value in replacements.items():
                if isinstance(key, tuple):
                    wrong, correct = key
                    string_key = f"{wrong} -> {correct}"
                    string_replacements[string_key] = value
                else:
                    string_replacements[str(key)] = value

            # Prepare results
            result = {
                "original_file": file_path,
                "corrected_file": str(output_path),
                "replacements": string_replacements,
                "total_replacements": sum(replacements.values()),
                "processing_time": elapsed_time
            }

            logger.info(f"Processed {file_path} in {elapsed_time:.2f} seconds with {sum(replacements.values())} replacements")
            return result

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return {
                "original_file": file_path,
                "error": str(e),
                "status": "error"
            }
