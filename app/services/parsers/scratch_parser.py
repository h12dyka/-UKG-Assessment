import json
import zipfile
from pathlib import Path
from typing import Dict, Any
from app.services.parsers.base_parser import BaseParser

class ScratchParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            if not zipfile.is_zipfile(file_path):
                return {
                    'success': False,
                    'summary': "Berkas bukan arsip Scratch .sb3 yang valid.",
                    'extracted_content': '',
                    'metadata': {},
                    'error': "Bukan file zip valid"
                }

            with zipfile.ZipFile(file_path, 'r') as zf:
                if 'project.json' not in zf.namelist():
                    return {
                        'success': False,
                        'summary': "Arsip .sb3 tidak mengandung project.json.",
                        'extracted_content': '',
                        'metadata': {},
                        'error': "project.json tidak ditemukan"
                    }

                with zf.open('project.json') as pf:
                    data = json.load(pf)

            targets = data.get('targets', [])
            sprites = []
            total_blocks = 0
            variables_list = []
            broadcasts_list = []
            sprite_details = []

            event_blocks = 0
            control_blocks = 0

            for target in targets:
                is_stage = target.get('isStage', False)
                name = target.get('name', 'Panggung' if is_stage else 'Sprite')
                blocks = target.get('blocks', {})
                costumes = target.get('costumes', [])
                sounds = target.get('sounds', [])
                variables = target.get('variables', {})
                broadcasts = target.get('broadcasts', {})

                for var_id, var_info in variables.items():
                    if isinstance(var_info, list) and len(var_info) > 0:
                        variables_list.append(str(var_info[0]))

                for b_id, b_name in broadcasts.items():
                    broadcasts_list.append(str(b_name))

                target_blocks_count = 0
                target_opcodes = []
                for b_id, b_data in blocks.items():
                    if isinstance(b_data, dict):
                        target_blocks_count += 1
                        total_blocks += 1
                        opcode = b_data.get('opcode', '')
                        target_opcodes.append(opcode)
                        if 'event_' in opcode:
                            event_blocks += 1
                        elif 'control_' in opcode:
                            control_blocks += 1

                if not is_stage:
                    sprites.append(name)

                costume_names = [c.get('name', '') for c in costumes if isinstance(c, dict)]
                detail = (
                    f"Karakter: '{name}' ({'Panggung/Latar' if is_stage else 'Sprite'})\n"
                    f" - Jumlah Blok Logika: {target_blocks_count}\n"
                    f" - Kostum/Tampilan: {len(costumes)} ({', '.join(costume_names[:5])})\n"
                    f" - Suara: {len(sounds)}\n"
                    f" - Opcodes Utama: {', '.join(set(target_opcodes[:10]))}"
                )
                sprite_details.append(detail)

            summary = (
                f"Proyek Animasi/Game Scratch (.sb3) memuat {len(sprites)} sprite, "
                f"{total_blocks} blok kode pemrograman ({control_blocks} kontrol perulangan/kondisi, {event_blocks} event pemicu)."
            )

            content = (
                f"=== ANALISIS ARSITEKTUR SCRATCH .SB3 ===\n"
                f"Total Sprite Karakter: {len(sprites)} ({', '.join(sprites) or 'Hanya Panggung'})\n"
                f"Total Blok Pemrograman: {total_blocks}\n"
                f"Blok Event (Ketika Ditekan/Dimulai): {event_blocks}\n"
                f"Blok Kontrol (If-Else / Perulangan Loop): {control_blocks}\n"
                f"Variabel Data Terdaftar: {', '.join(set(variables_list)) or 'Tidak ada'}\n"
                f"Pesan Siaran (Broadcast): {', '.join(set(broadcasts_list)) or 'Tidak ada'}\n\n"
                f"--- RINCIAN PER SPRITE & PANGGUNG ---\n" + "\n\n".join(sprite_details)
            )

            return {
                'success': True,
                'summary': summary,
                'extracted_content': content,
                'metadata': {
                    'type': 'scratch',
                    'total_blocks': total_blocks,
                    'sprites_count': len(sprites),
                    'sprites': sprites,
                    'control_blocks': control_blocks,
                    'event_blocks': event_blocks,
                    'variables': list(set(variables_list))
                },
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca Scratch .sb3: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'scratch', 'error': str(e)},
                'error': str(e)
            }
