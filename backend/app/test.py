import os
import re
from pathlib import Path

def convert_srt_to_txt(srt_path, txt_path):
    with open(srt_path, 'r', encoding='utf-8') as srt_file:
        lines = srt_file.readlines()

    output_lines = []
    for line in lines:
        # Remove timestamp lines and index numbers
        if re.match(r'^\d+\s*$', line.strip()):
            continue
        if re.match(r'^\d{2}:\d{2}:\d{2},\d{3} -->', line.strip()):
            continue
        if line.strip() == '':
            continue
        output_lines.append(line.strip())

    with open(txt_path, 'w', encoding='utf-8') as txt_file:
        txt_file.write('\n'.join(output_lines))


def batch_convert_srt_to_txt(source_folder, output_folder):
    source_folder = Path(source_folder)
    output_folder = Path(output_folder)

    if not source_folder.exists():
          print('dsafdsa')

    output_folder.mkdir(parents=True, exist_ok=True)

    for srt_file in source_folder.rglob('*.srt'):
        txt_filename = srt_file.stem + '.txt'
        txt_output_path = output_folder / txt_filename
        convert_srt_to_txt(srt_file, txt_output_path)
        print(f'Converted: {srt_file} -> {txt_output_path}')

# Example usage
source = '/Users/jiasheng/Downloads/CS7646_Lectures/02_01_So_you_want_to_be_a_hedge_fund_manager_subtitles'
output = '/Users/jiasheng/Downloads/CS7646_Lectures_txt'
print(source, output)
batch_convert_srt_to_txt(source, output)
