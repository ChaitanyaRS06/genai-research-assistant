import PyPDF2
from typing import List, Tuple
from pathlib import Path
import re
from dataclasses import dataclass

@dataclass
class DocumentChunk:
    """Represents a chunk of text from a document"""
    text: str
    chunk_index: int
    page_number: int
    char_count: int

class PDFProcessor:
    """Handles PDF text extraction and chunking"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize PDF processor.
        
        Args:
            chunk_size: Target size for each text chunk (in characters)
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, file_path: Path) -> List[Tuple[str, int]]:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of (text, page_number) tuples
        """
        pages_text = []
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    
                    # Clean up the extracted text
                    text = self._clean_text(text)
                    
                    if text.strip():  # Only add non-empty pages
                        pages_text.append((text, page_num))
                        
        except Exception as e:
            raise ValueError(f"Error reading PDF file: {str(e)}")
        
        return pages_text
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted PDF text.
        
        Args:
            text: Raw text from PDF
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'[^\w\s\.,!?;:()\-\'"]+', ' ', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()
    
    def chunk_text(self, pages_text: List[Tuple[str, int]]) -> List[DocumentChunk]:
        """
        Split text into overlapping chunks for better retrieval.
        
        Args:
            pages_text: List of (text, page_number) tuples
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        chunk_index = 0
        
        for page_text, page_num in pages_text:
            # If page is smaller than chunk_size, treat it as one chunk
            if len(page_text) <= self.chunk_size:
                chunks.append(DocumentChunk(
                    text=page_text,
                    chunk_index=chunk_index,
                    page_number=page_num,
                    char_count=len(page_text)
                ))
                chunk_index += 1
                continue
            
            # Split large pages into overlapping chunks
            page_chunks = self._split_text_with_overlap(page_text, page_num)
            
            for chunk_text in page_chunks:
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    page_number=page_num,
                    char_count=len(chunk_text)
                ))
                chunk_index += 1
        
        return chunks
    
    def _split_text_with_overlap(self, text: str, page_num: int) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to split
            page_num: Page number for this text
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position for this chunk
            end = start + self.chunk_size
            
            # If this is not the last chunk, try to break at a sentence
            if end < len(text):
                # Look for sentence endings within the last 200 characters
                search_start = max(end - 200, start)
                sentence_end = text.rfind('.', search_start, end)
                
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            
            # Ensure we don't go backwards
            if start <= 0:
                start = end
        
        return chunks
    
    def process_pdf(self, file_path: Path) -> List[DocumentChunk]:
        """
        Complete PDF processing pipeline.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of processed document chunks
        """
        # Extract text from PDF
        pages_text = self.extract_text_from_pdf(file_path)
        
        if not pages_text:
            raise ValueError("No text could be extracted from the PDF")
        
        # Chunk the text
        chunks = self.chunk_text(pages_text)
        
        return chunks

# Utility function for easy usage
def process_pdf_file(file_path: Path, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[DocumentChunk]:
    """
    Process a PDF file and return chunks.
    
    Args:
        file_path: Path to PDF file
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of DocumentChunk objects
    """
    processor = PDFProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return processor.process_pdf(file_path)