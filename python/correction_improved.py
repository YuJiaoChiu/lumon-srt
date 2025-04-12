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

def should_correct(wrong: str, protection_dict: Dict[str, str]) -> bool:
    """
    Determine if a term should be corrected based on protection dictionary.
    
    This is a simplified version based on sub2024_9.py implementation.

    Args:
        wrong (str): The term to check for correction
        protection_dict (Dict[str, str]): Dictionary of protected terms

    Returns:
        bool: True if the term should be corrected, False otherwise
    """
    wrong_lower = wrong.lower()
    for protected in protection_dict.keys():
        protected_lower = protected.lower()
        # If wrong is exactly a protected term, don't correct it
        if protected_lower == wrong_lower:
            return False
        # If wrong is contained within a protected term, don't correct it
        if wrong_lower in protected_lower:
            return False
        # If a protected term is contained within wrong, we might need to check context
        # For simplicity, we'll allow correction in this case
    return True

def correct_subtitles(text: str, correction_dict: Dict[str, str], protection_dict: Dict[str, str]) -> Tuple[str, Dict[str, int]]:
    """
    Correct subtitles based on correction and protection dictionaries.
    
    This implementation combines the best practices from both implementations.

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
    
    # Sort correction items by length (longest first) for proper matching
    sorted_correction_items = sorted(correction_dict.items(), key=lambda x: len(x[0]), reverse=True)
    
    # Process the file line by line
    lines = text.split('\n')
    corrected_lines = []
    replacements = Counter()
    
    for i, line in enumerate(lines):
        # Skip timestamp lines
        if '-->' in line:
            corrected_lines.append(line)
            continue
            
        # Skip lines that are just parenthetical comments
        if re.match(r'^\s*\([^)]*\)\s*$', line):
            logger.debug(f"Skipping parenthetical line: {line}")
            continue
            
        # Store original line for logging
        original_line = line
        replaced_positions = []  # Track replaced positions to avoid overlaps
        
        # Apply corrections
        for wrong, correct in sorted_correction_items:
            if should_correct(wrong, protection_dict):
                # Create pattern with case-insensitive matching
                pattern = re.compile(re.escape(wrong), re.IGNORECASE)
                
                # Define replacement function to handle case preservation and position tracking
                def replace_func(match):
                    start, end = match.span()
                    # Check if this position overlaps with any already replaced position
                    if any(start < pos[1] and end > pos[0] for pos in replaced_positions):
                        return match.group(0)  # If already replaced, return original text
                    
                    # Get the matched text to preserve case
                    matched_text = match.group(0)
                    replacement = correct if correct else ''
                    
                    # Preserve case
                    if matched_text.isupper() and replacement:
                        replacement = replacement.upper()
                    elif matched_text.istitle() and replacement:
                        replacement = replacement.capitalize()
                    
                    # Record this position as replaced
                    replaced_positions.append((start, end))
                    replacements[(wrong, correct)] += 1
                    
                    logger.debug(f"Replaced '{matched_text}' with '{replacement}' at position {start}-{end}")
                    return replacement
                
                # Apply the replacement
                new_line, count = pattern.subn(replace_func, line)
                if count > 0:
                    line = new_line
        
        # Log changes if any were made
        if original_line != line:
            logger.info(f"Line {i+1} changed: '{original_line}' -> '{line}'")
            
        corrected_lines.append(line)
    
    # Convert Counter to serializable format for JSON
    serializable_replacements = {}
    for (wrong, correct), count in replacements.items():
        serializable_replacements[f"{wrong} -> {correct}"] = count
    
    elapsed_time = time.time() - start_time
    logger.info(f"Correction completed in {elapsed_time:.2f} seconds with {sum(replacements.values())} replacements")
    
    return '\n'.join(corrected_lines), serializable_replacements
