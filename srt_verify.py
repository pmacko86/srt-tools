#!/usr/bin/env python3

import argparse
import sys
from functools import total_ordering
from typing import List, Optional


@total_ordering
class SRTTime:
    """
    Represents a timestamp in SRT subtitle format (HH:MM:SS,mmm).

    This class handles parsing, comparison, and arithmetic operations on SRT timestamps.
    It supports the standard SRT time format with hours, minutes, seconds, and milliseconds.
    """

    def __init__(
        self, hours: int, minutes: int, seconds: int, milliseconds: int
    ) -> None:
        """
        Initialize an SRTTime object.

        Args:
            hours: Hour component (0-23)
            minutes: Minute component (0-59)
            seconds: Second component (0-59)
            milliseconds: Millisecond component (0-999)
        """
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
        self.milliseconds = milliseconds

    @staticmethod
    def parse(time_str: str) -> "SRTTime":
        """
        Parse a time string in SRT format (HH:MM:SS,mmm) into an SRTTime object.

        Args:
            time_str: Time string in format "HH:MM:SS,mmm" or "HH:MM:SS"

        Returns:
            SRTTime object representing the parsed time

        Raises:
            ValueError: If the time format is invalid
        """
        parts = time_str.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid time format: {time_str}")
        hours = int(parts[0])
        minutes = int(parts[1])
        sec_parts = parts[2].split(",")
        if len(sec_parts) == 2:
            seconds = int(sec_parts[0])
            milliseconds = int(sec_parts[1].ljust(3, "0")[:3])
        else:
            # fallback if comma is missing, treat as seconds only
            seconds = int(float(sec_parts[0]))
            milliseconds = 0
        return SRTTime(hours, minutes, seconds, milliseconds)

    def __lt__(self, other: "SRTTime") -> bool:
        """
        Compare if this time is less than another time.

        Args:
            other: Another SRTTime object to compare with

        Returns:
            True if this time is earlier than the other time
        """
        return (self.hours, self.minutes, self.seconds, self.milliseconds) < (
            other.hours,
            other.minutes,
            other.seconds,
            other.milliseconds,
        )

    def __str__(self) -> str:
        """
        Return the string representation of the time in SRT format.

        Returns:
            Time formatted as "HH:MM:SS,mmm"
        """
        return f"{self.hours:02}:{self.minutes:02}:{self.seconds:02},{self.milliseconds:03}"

    def average(self, other: "SRTTime") -> "SRTTime":
        """
        Calculate the average time between this time and another time.

        Args:
            other: Another SRTTime object to average with

        Returns:
            SRTTime object representing the midpoint between the two times
        """
        total_ms1 = (
            self.hours * 3600000
            + self.minutes * 60000
            + self.seconds * 1000
            + self.milliseconds
        )
        total_ms2 = (
            other.hours * 3600000
            + other.minutes * 60000
            + other.seconds * 1000
            + other.milliseconds
        )
        avg_ms = (total_ms1 + total_ms2) // 2
        hours = avg_ms // 3600000
        avg_ms %= 3600000
        minutes = avg_ms // 60000
        avg_ms %= 60000
        seconds = avg_ms // 1000
        milliseconds = avg_ms % 1000
        return SRTTime(hours, minutes, seconds, milliseconds)


class SRTEntry:
    """
    Represents a single subtitle entry in an SRT file.

    Each entry contains an ID, start/end times, text content, and optional line number
    information for error reporting.
    """

    def __init__(
        self,
        id: int,
        start_time: SRTTime,
        end_time: SRTTime,
        text: List[str],
        line_number: Optional[int] = None,
    ) -> None:
        """
        Initialize an SRTEntry object.

        Args:
            id: Unique identifier for the subtitle entry
            start_time: When the subtitle should appear
            end_time: When the subtitle should disappear
            text: List of text lines for the subtitle
            line_number: Optional line number in source file for error reporting
        """
        self.id = id
        self.start_time = start_time
        self.end_time = end_time
        self.text = text
        self.line_number = line_number

    def __str__(self) -> str:
        """
        Return the string representation of the subtitle entry in SRT format.

        Returns:
            Formatted subtitle entry with ID, timing, and text
        """
        text_str = "\n".join(self.text)
        return f"{self.id}\n{self.start_time} --> {self.end_time}\n{text_str}"


class SRTFile:
    """
    Represents a complete SRT subtitle file containing multiple entries.

    This class handles parsing SRT content, managing subtitle entries, and providing
    functionality for validation and error correction.
    """

    entries: List[SRTEntry]
    warnings: Optional[List[str]]

    def __init__(self, entries: Optional[List[SRTEntry]] = None) -> None:
        """
        Initialize an SRTFile object.

        Args:
            entries: Optional list of SRTEntry objects
        """
        self.entries = entries if entries is not None else []
        self.warnings: List[str] = []

    def add_entry(self, entry: SRTEntry) -> None:
        """
        Add a subtitle entry to the file.

        Args:
            entry: SRTEntry object to add
        """
        self.entries.append(entry)

    def __str__(self) -> str:
        """
        Return the string representation of the entire SRT file.

        Returns:
            Complete SRT file content with all entries
        """
        return "\n\n".join(str(entry) for entry in self.entries)

    @staticmethod
    def parse(
        srt_content: str, renumber: bool = False, fix_errors: bool = False
    ) -> "SRTFile":
        """
        Parse SRT content from a string into an SRTFile object.

        Args:
            srt_content: Raw SRT file content as string
            renumber: Whether to renumber entries sequentially
            fix_errors: Whether to attempt automatic error correction

        Returns:
            SRTFile object containing parsed entries

        Raises:
            ValueError: If the SRT format is invalid and fix_errors is False
        """
        entries: List[SRTEntry] = []
        new_id: int = 1
        warnings: List[str] = []

        i: int = 0
        lines: List[str] = srt_content.strip().split("\n")
        while i < len(lines):
            l: str = lines[i].strip()
            if not l:
                i += 1
                continue

            # Parse the entry ID line
            line_number: int = i + 1
            id: int
            if "-->" in l or "→" in l:
                if not fix_errors:
                    raise ValueError(
                        f"Expected integer entry ID at line {line_number}, got: {lines[i]!r}"
                    )
                if renumber:
                    id = new_id
                    new_id += 1
                    warnings.append(
                        f"Missing entry ID at line {line_number}; assigned new ID {id}."
                    )
                else:
                    raise ValueError(
                        f"Expected integer entry ID at line {line_number}; "
                        f"must turn on renumbering to fix this error."
                    )
            else:
                try:
                    id = int(lines[i])
                except ValueError:
                    raise ValueError(
                        f"Expected integer entry ID at line {i+1}, got: {lines[i]!r}"
                    )
                i += 1
                if renumber:
                    id = new_id
                    new_id += 1

            # Parse the time range
            l = lines[i].strip()
            if "-->" not in l:
                if "→" in l and fix_errors:
                    l = l.replace("→", "-->")
                    warnings.append(
                        f"Replaced '→' with '-->' at line {i+1}."
                    )
                else:
                    raise ValueError(
                        f"Expected time range at line {i+1}, got: {lines[i]!r}"
                    )
            time_range: List[str] = l.split(" --> ")
            start_time: SRTTime = SRTTime.parse(time_range[0].strip())
            end_time: SRTTime = SRTTime.parse(time_range[1].strip())
            i += 1

            # Parse the text lines
            text_lines: List[str] = []
            while i < len(lines) and lines[i].strip():
                l = lines[i].strip()
                if "-->" in l:
                    raise ValueError(
                        f"Unexpected time range in text at line {i+1}, got: {lines[i]!r}"
                    )
                text_lines.append(l)
                i += 1
            entries.append(SRTEntry(id, start_time, end_time, text_lines, line_number))

        f: SRTFile = SRTFile(entries)
        f.warnings = warnings
        return f


def verify_srt(srt: SRTFile, fix_errors: bool = False) -> List[str]:
    """
    Verify the integrity of an SRT file and optionally fix common errors.

    This function checks for:
    - Missing start or end times
    - Invalid time ranges (start >= end)
    - Overlapping subtitle entries

    Args:
        srt: SRTFile object to verify
        fix_errors: Whether to attempt automatic error correction

    Returns:
        List of error messages found during verification
    """
    errors: List[str] = []
    prev: Optional[SRTEntry] = None
    for entry in srt.entries:
        if not entry.start_time or not entry.end_time:
            errors.append(
                f"Entry {entry.id} on line {entry.line_number} has missing start or end time."
            )
        if entry.start_time >= entry.end_time:
            errors.append(
                f"Entry {entry.id} on line {entry.line_number} has invalid time range: "
                f"{entry.start_time} - {entry.end_time}."
            )

        if prev is not None:
            if entry.start_time < prev.end_time:
                if fix_errors:
                    midpoint: SRTTime = prev.end_time.average(entry.start_time)
                    prev.end_time = midpoint  # Adjust previous end time to midpoint
                    entry.start_time = midpoint  # Adjust start time to midpoint
                else:
                    errors.append(
                        f"Entry {entry.id} on line {entry.line_number} overlaps with "
                        f"entry {prev.id} on line {prev.line_number}."
                    )
        prev = entry

    return errors


def main() -> None:
    """
    Main entry point for the SRT verification tool.

    Parses command line arguments, reads the SRT file, performs verification,
    and outputs results with optional error fixing.
    """
    parser = argparse.ArgumentParser(description="Verify an SRT subtitle file.")
    parser.add_argument("filename", help="Path to the SRT file to verify")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix errors in the SRT file",
    )
    parser.add_argument(
        "--renumber", action="store_true", help="Renumber subtitle entries sequentially"
    )
    args = parser.parse_args()

    with open(args.filename, "r", encoding="utf-8") as f:
        srt_content = f.read()

    srt = SRTFile.parse(srt_content, renumber=args.renumber, fix_errors=args.fix)
    if hasattr(srt, "warnings") and srt.warnings:
        print("Warnings:", file=sys.stderr)
        for w in srt.warnings:
            print(w, file=sys.stderr)
        print(file=sys.stderr)

    print(f"# entries: {format(len(srt.entries))}\n", file=sys.stderr)

    result = verify_srt(srt, fix_errors=args.fix)
    if result and args.fix:
        # Hopefully we fixed the errors, so we verify again
        result = verify_srt(srt)

    if result:
        print("Errors:", file=sys.stderr)
        for error in result:
            print(error, file=sys.stderr)

    # Print the SRT contents
    if args.fix or args.renumber:
        print("Fixed SRT contents:", file=sys.stderr)
        print(srt)


if __name__ == "__main__":
    main()
