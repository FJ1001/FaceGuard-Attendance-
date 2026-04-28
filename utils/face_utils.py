"""
File handling utilities
File operations and management functions
"""
import os
import shutil
import json
import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import tempfile

from utils.constants import ALLOWED_IMAGE_EXTENSIONS, ALLOWED_IMAGE_MIMES
from utils.helperrs import clean_filename, generate_unique_id

logger = logging.getLogger(__name__)

class FileManager:
    """File management utility class"""
    
    def __init__(self, base_dir: Union[str, Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.ensure_directory_exists(self.base_dir)
    
    def ensure_directory_exists(self, directory: Union[str, Path]) -> Path:
        """Ensure directory exists, create if it doesn't"""
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def create_backup_filename(self, original_filename: str) -> str:
        """Create backup filename with timestamp"""
        file_path = Path(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{file_path.stem}_{timestamp}_backup{file_path.suffix}"
    
    def get_safe_filename(self, filename: str, directory: Union[str, Path] = None) -> str:
        """Get safe filename avoiding conflicts"""
        if directory:
            dir_path = Path(directory)
        else:
            dir_path = self.base_dir
        
        # Clean the filename
        safe_name = clean_filename(filename)
        file_path = dir_path / safe_name
        
        # If file exists, append counter
        counter = 1
        original_path = file_path
        
        while file_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            file_path = dir_path / f"{stem}_{counter}{suffix}"
            counter += 1
        
        return str(file_path)
    
    def copy_file(self, source: Union[str, Path], destination: Union[str, Path]) -> bool:
        """Copy file with error handling"""
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            if not source_path.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return False
            
            # Ensure destination directory exists
            self.ensure_directory_exists(dest_path.parent)
            
            shutil.copy2(source_path, dest_path)
            logger.info(f"File copied: {source_path} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    def move_file(self, source: Union[str, Path], destination: Union[str, Path]) -> bool:
        """Move file with error handling"""
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            if not source_path.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return False
            
            # Ensure destination directory exists
            self.ensure_directory_exists(dest_path.parent)
            
            shutil.move(str(source_path), str(dest_path))
            logger.info(f"File moved: {source_path} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False
    
    def delete_file(self, file_path: Union[str, Path]) -> bool:
        """Delete file with error handling"""
        try:
            path = Path(file_path)
            
            if path.exists():
                path.unlink()
                logger.info(f"File deleted: {path}")
                return True
            else:
                logger.warning(f"File does not exist: {path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def get_file_info(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Get file information"""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return None
            
            stat = path.stat()
            
            return {
                'name': path.name,
                'stem': path.stem,
                'suffix': path.suffix,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'is_file': path.is_file(),
                'is_dir': path.is_dir(),
                'absolute_path': str(path.absolute())
            }
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def validate_image_file(self, file_path: Union[str, Path]) -> tuple[bool, str]:
        """Validate image file"""
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                return False, "File does not exist"
            
            # Check extension
            if path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
                return False, f"Invalid file extension. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            
            # Check file size (max 10MB)
            file_info = self.get_file_info(path)
            if file_info and file_info['size_mb'] > 10:
                return False, "File too large. Maximum size is 10MB"
            
            return True, "Valid image file"
            
        except Exception as e:
            logger.error(f"Error validating image file: {e}")
            return False, f"Validation error: {str(e)}"

def save_json_file(data: Dict[str, Any], file_path: Union[str, Path]) -> bool:
    """Save data as JSON file"""
    try:
        path = Path(file_path)
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"JSON file saved: {path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving JSON file: {e}")
        return False

def load_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Load data from JSON file"""
    try:
        path = Path(file_path)
        
        if not path.exists():
            logger.warning(f"JSON file does not exist: {path}")
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"JSON file loaded: {path}")
        return data
        
    except Exception as e:
        logger.error(f"Error loading JSON file: {e}")
        return None

def save_csv_file(data: List[Dict[str, Any]], file_path: Union[str, Path], 
                  fieldnames: Optional[List[str]] = None) -> bool:
    """Save data as CSV file"""
    try:
        if not data:
            logger.warning("No data to save")
            return False
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get fieldnames from first row if not provided
        if not fieldnames:
            fieldnames = list(data[0].keys())
        
        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"CSV file saved: {path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving CSV file: {e}")
        return False

def load_csv_file(file_path: Union[str, Path]) -> Optional[List[Dict[str, Any]]]:
    """Load data from CSV file"""
    try:
        path = Path(file_path)
        
        if not path.exists():
            logger.warning(f"CSV file does not exist: {path}")
            return None
        
        data = []
        with open(path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            data = list(reader)
        
        logger.info(f"CSV file loaded: {path} ({len(data)} rows)")
        return data
        
    except Exception as e:
        logger.error(f"Error loading CSV file: {e}")
        return None

def create_temp_file(suffix: str = '', prefix: str = 'temp_', delete: bool = False) -> str:
    """Create temporary file and return path"""
    try:
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            prefix=prefix,
            delete=delete
        )
        
        temp_path = temp_file.name
        
        if not delete:
            temp_file.close()
        
        logger.info(f"Temporary file created: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Error creating temporary file: {e}")
        return ""

def create_temp_directory(prefix: str = 'temp_') -> str:
    """Create temporary directory and return path"""
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        logger.info(f"Temporary directory created: {temp_dir}")
        return temp_dir
        
    except Exception as e:
        logger.error(f"Error creating temporary directory: {e}")
        return ""

def cleanup_temp_files(temp_paths: List[str]) -> int:
    """Cleanup temporary files and directories"""
    cleaned_count = 0
    
    for temp_path in temp_paths:
        try:
            path = Path(temp_path)
            
            if path.exists():
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
                
                cleaned_count += 1
                logger.info(f"Cleaned up temporary path: {path}")
                
        except Exception as e:
            logger.error(f"Error cleaning up {temp_path}: {e}")
    
    return cleaned_count

def get_directory_size(directory: Union[str, Path]) -> int:
    """Get total size of directory in bytes"""
    try:
        total_size = 0
        dir_path = Path(directory)
        
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
        
    except Exception as e:
        logger.error(f"Error calculating directory size: {e}")
        return 0

def compress_directory(source_dir: Union[str, Path], output_file: Union[str, Path]) -> bool:
    """Compress directory to zip file"""
    try:
        shutil.make_archive(
            str(Path(output_file).with_suffix('')), 
            'zip', 
            str(source_dir)
        )
        
        logger.info(f"Directory compressed: {source_dir} -> {output_file}.zip")
        return True
        
    except Exception as e:
        logger.error(f"Error compressing directory: {e}")
        return False

def extract_archive(archive_path: Union[str, Path], extract_to: Union[str, Path]) -> bool:
    """Extract archive file"""
    try:
        shutil.unpack_archive(str(archive_path), str(extract_to))
        logger.info(f"Archive extracted: {archive_path} -> {extract_to}")
        return True
        
    except Exception as e:
        logger.error(f"Error extracting archive: {e}")
        return False

# Global file manager instance
default_file_manager = FileManager()

# Convenience functions using default file manager
def ensure_dir_exists(directory: Union[str, Path]) -> Path:
    """Ensure directory exists using default file manager"""
    return default_file_manager.ensure_directory_exists(directory)

def get_safe_path(filename: str, directory: Union[str, Path] = None) -> str:
    """Get safe file path using default file manager"""
    return default_file_manager.get_safe_filename(filename, directory)
