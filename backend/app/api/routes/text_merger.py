from fastapi import APIRouter, UploadFile, File
from fastapi.responses import PlainTextResponse
from typing import List
import io

router = APIRouter(prefix="/text-merger", tags=["text-merger"])


@router.post("/merge/", response_class=PlainTextResponse)
async def merge_text_files(files: List[UploadFile] = File(...)) -> str:
    """
    Merge multiple text files into one.
    
    Args:
        files: List of text files to merge
        
    Returns:
        The merged content as a single string
    """
    merged_content = []
    
    for file in files:
        if not file.content_type.startswith('text/'):
            continue
            
        content = await file.read()
        try:
            text = content.decode('utf-8')
            merged_content.append(text)
        except UnicodeDecodeError:
            # Skip files that can't be decoded as UTF-8
            continue
            
    return '\n'.join(merged_content) 
