import re
import logging
from collections import Counter
from typing import Dict, Tuple, Any, List
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_srt(text: str) -> bool:
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

    # For simplicity, just check if there's a timestamp pattern
    # This is a more lenient validation that works for most SRT files
    return True

def word_boundary_match(text: str, term: str) -> List[Tuple[int, int]]:
    """
    Find all occurrences of a term with word boundaries.

    Args:
        text (str): The text to search in
        term (str): The term to search for

    Returns:
        List[Tuple[int, int]]: List of (start, end) positions of matches
    """
    # Escape special regex characters in the term
    escaped_term = re.escape(term)
    # Create pattern with word boundaries
    pattern = re.compile(r'\b' + escaped_term + r'\b', re.IGNORECASE)

    # Find all matches
    matches = []
    for match in pattern.finditer(text):
        matches.append(match.span())

    return matches

def correct_subtitles(text: str, correction_dict: Dict[str, str], protection_dict: Dict[str, str]) -> Tuple[str, Dict[str, int]]:
    """
    Correct subtitles based on correction and protection dictionaries.

    Args:
        text (str): The SRT file content
        correction_dict (Dict[str, str]): Dictionary of terms to correct
        protection_dict (Dict[str, str]): Dictionary of terms to protect

    Returns:
        Tuple[str, Dict[str, int]]: (corrected_text, replacements_counter)
    """
    # Validate SRT format
    if not validate_srt(text):
        logger.warning("Invalid SRT format detected")
        return text, {"error": "Invalid SRT format"}

    start_time = time.time()

    # Log dictionary sizes
    logger.info(f"Correction dictionary size: {len(correction_dict)} items")
    logger.info(f"Protection dictionary size: {len(protection_dict)} items")

    # Log a sample of the correction dictionary
    sample_items = list(correction_dict.items())[:5]
    logger.info(f"Sample correction items: {sample_items}")
    replacements = Counter()

    # Pre-process protection dictionary for faster lookup
    protected_terms_lower = {term.lower(): term for term in protection_dict.keys()}

    # Compile regex patterns for protected terms (for faster matching)
    protected_patterns = {}
    for term in protected_terms_lower.keys():
        if term.strip():
            # Escape special regex characters
            escaped_term = re.escape(term)
            # Use word boundaries only for non-Chinese terms
            if any(ord(c) > 127 for c in term):  # Contains non-ASCII (likely Chinese)
                protected_patterns[term] = re.compile(escaped_term, re.IGNORECASE)
            else:  # ASCII only (English, etc.)
                protected_patterns[term] = re.compile(r'\b' + escaped_term + r'\b', re.IGNORECASE)

    # Pre-compile regex patterns for correction terms (for faster matching)
    correction_patterns = {}
    for wrong, correct in correction_dict.items():
        if wrong.strip():
            # Escape special regex characters
            escaped_term = re.escape(wrong)
            # Use word boundaries only for non-Chinese terms
            if any(ord(c) > 127 for c in wrong):  # Contains non-ASCII (likely Chinese)
                correction_patterns[wrong] = (re.compile(escaped_term, re.IGNORECASE), correct)
            else:  # ASCII only (English, etc.)
                correction_patterns[wrong] = (re.compile(r'\b' + escaped_term + r'\b', re.IGNORECASE), correct)

    # Sort correction items by length (longest first) for proper matching
    sorted_correction_items = sorted(correction_dict.items(), key=lambda x: len(x[0]), reverse=True)

    def should_correct(term_to_check: str, line: str) -> bool:
        """
        Determine if a term should be corrected based on protection dictionary.

        Args:
            term_to_check (str): The specific term we're checking for correction
            line (str): The line containing the term

        Returns:
            bool: True if the term should be corrected, False otherwise
        """
        term_lower = term_to_check.lower()

        # Check if the term is exactly a protected term
        if term_lower in protected_terms_lower:
            return False

        # Check if the term appears as a protected term with word boundaries
        for protected_term, pattern in protected_patterns.items():
            if pattern.search(line):
                # If the protected term overlaps with our term, don't correct
                if term_lower in protected_term or protected_term in term_lower:
                    return False

        return True

    # Process the text in chunks for better performance
    def process_subtitle_block(block: str) -> str:
        # Log the block we're processing
        logger.info(f"Processing subtitle block: {block}")

        # Extract the subtitle text part (after the timestamp line)
        lines = block.split('\n')
        subtitle_text = ''
        timestamp_found = False

        for i, line in enumerate(lines):
            if '-->' in line:  # This is a timestamp line
                timestamp_found = True
                continue
            if timestamp_found and line.strip():  # This is subtitle text after timestamp
                subtitle_text += line + '\n'

        if not subtitle_text.strip():
            logger.info("No subtitle text found in block")
            return block

        logger.info(f"Extracted subtitle text: {subtitle_text}")

        # Skip blocks that are just parenthetical comments
        if re.match(r'^\s*\([^)]*\)\s*$', subtitle_text):
            logger.info("Skipping parenthetical block")
            return block

        # Process the subtitle text
        original_subtitle_text = subtitle_text
        replaced_positions = []  # Track replaced positions to avoid overlaps

        # Apply corrections with word boundary matching
        for wrong, correct in sorted_correction_items:
            # Log the term we're checking
            logger.info(f"Checking term: '{wrong}' -> '{correct}'")

            if should_correct(wrong, subtitle_text):
                logger.info(f"Term '{wrong}' should be corrected")
                pattern, replacement = correction_patterns.get(wrong, (None, correct))
                if not pattern:
                    logger.info(f"No pattern found for '{wrong}'")
                    continue

                # Log the pattern we're using
                logger.info(f"Using pattern: {pattern.pattern}")

                # Find all matches
                matches = list(pattern.finditer(subtitle_text))
                logger.info(f"Found {len(matches)} matches for '{wrong}'")

                for match in matches:
                    start, end = match.span()
                    matched_text = subtitle_text[start:end]
                    logger.info(f"Match: '{matched_text}' at positions {start}-{end}")

                    # Check if this position overlaps with any already replaced position
                    if any(start < pos[1] and end > pos[0] for pos in replaced_positions):
                        logger.info(f"Skipping overlapping match at {start}-{end}")
                        continue

                    # Get the matched text to preserve case
                    matched_text = subtitle_text[start:end]
                    final_replacement = replacement if replacement else ''

                    # Preserve case
                    if matched_text.isupper() and final_replacement:
                        final_replacement = final_replacement.upper()
                    elif matched_text.istitle() and final_replacement:
                        final_replacement = final_replacement.capitalize()

                    # Apply the replacement
                    subtitle_text = subtitle_text[:start] + final_replacement + subtitle_text[end:]

                    # Adjust positions of subsequent replacements
                    length_diff = len(final_replacement) - len(matched_text)
                    replaced_positions = [(pos[0] + length_diff if pos[0] > end else pos[0],
                                         pos[1] + length_diff if pos[1] > end else pos[1])
                                         for pos in replaced_positions]

                    # Record this position as replaced
                    replaced_positions.append((start, start + len(final_replacement)))
                    replacements[(wrong, correct)] += 1

                    logger.info(f"Replaced '{matched_text}' with '{final_replacement}'")

        # If subtitle text was changed, update the original block
        if original_subtitle_text != subtitle_text:
            logger.info(f"Subtitle text changed: '{original_subtitle_text}' -> '{subtitle_text}'")

            # Reconstruct the block with the corrected subtitle text
            new_block = ''
            timestamp_found = False
            for line in lines:
                new_block += line + '\n'
                if '-->' in line:  # After timestamp line, insert the corrected subtitle text
                    timestamp_found = True
                    new_block += subtitle_text

            return new_block.rstrip()

        return block

    # Split text into subtitle blocks (separated by blank lines)
    blocks = re.split(r'\n\s*\n', text)
    logger.info(f"Split text into {len(blocks)} blocks")
    for i, block in enumerate(blocks):
        logger.info(f"Block {i}: {block}")

    corrected_blocks = [process_subtitle_block(block) for block in blocks]
    corrected_text = '\n\n'.join(corrected_blocks)

    # Convert Counter to serializable format for JSON
    serializable_replacements = {}
    for (wrong, correct), count in replacements.items():
        serializable_replacements[f"{wrong} -> {correct}"] = count

    elapsed_time = time.time() - start_time
    logger.info(f"Correction completed in {elapsed_time:.2f} seconds with {sum(replacements.values())} replacements")

    return corrected_text, serializable_replacements
