from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response
import tempfile
import os
from typing import List
import shutil
from datetime import timedelta
import zipfile
import io

router = APIRouter(prefix="/convert", tags=["converter"])

def convert_srt_to_txt(srt_content: str) -> str:
    """Convert SRT content to plain text."""
    lines = srt_content.split('\n')
    text_lines = []
    current_text = ""
    
    for line in lines:
        line = line.strip()
        # Skip empty lines, subtitle numbers, and timestamp lines
        if (not line or 
            line.isdigit() or 
            '-->' in line):
            if current_text:
                text_lines.append(current_text)
                current_text = ""
            continue
        
        current_text += " " + line if current_text else line
    
    if current_text:
        text_lines.append(current_text)
    
    return '\n'.join(text_lines)

@router.post("/srt-to-txt/single")
async def convert_single_file(file: UploadFile = File(...)):
    """Convert a single SRT file to TXT."""
    if not file.filename.endswith('.srt'):
        return {"error": "File must be an SRT file"}
    
    content = await file.read()
    srt_content = content.decode('utf-8')
    txt_content = convert_srt_to_txt(srt_content)
    
    return Response(
        content=txt_content.encode('utf-8'),
        media_type='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{os.path.splitext(file.filename)[0]}.txt"'
        }
    )

@router.post("/srt-to-txt/batch")
async def convert_multiple_files(files: List[UploadFile] = File(...)):
    """Convert multiple SRT files to TXT and return as ZIP."""
    if not all(file.filename.endswith('.srt') for file in files):
        return {"error": "All files must be SRT files"}
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            content = await file.read()
            srt_content = content.decode('utf-8')
            txt_content = convert_srt_to_txt(srt_content)
            
            output_filename = os.path.splitext(file.filename)[0] + '.txt'
            zip_file.writestr(output_filename, txt_content)
    
    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type='application/zip',
        headers={
            'Content-Disposition': 'attachment; filename="converted_files.zip"'
        }
    ) 
