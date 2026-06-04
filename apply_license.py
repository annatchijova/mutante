#!/usr/bin/env python3
"""
apply_license.py — Automatización de encabezados Apache 2.0 para MUTANTE.
"""

import os

LICENSE_HEADER = """# Copyright 2026 Anna Tchijova, Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""

TARGET_DIR = os.path.expanduser("~/MUTANTE")

def patch_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Evitamos duplicaciones innecesarias
    if "Apache License, Version 2.0" in content or "Anna Tchijova" in content:
        print(f"[-] Omitido (ya licenciado): {file_path}")
        return

    lines = content.splitlines(keepends=True)
    new_content = []
    
    # Manejo correcto del Shebang o declaraciones de encoding de Python
    has_shebang = lines and (lines[0].startswith("#!") or "coding:" in lines[0])
    has_encoding_line2 = len(lines) > 1 and "coding:" in lines[1]

    if has_shebang:
        new_content.append(lines[0])
        if has_encoding_line2:
            new_content.append(lines[1])
            remaining_lines = lines[2:]
        else:
            remaining_lines = lines[1:]
    else:
        remaining_lines = lines

    # Inyección limpia del bloque de licencia
    new_content.append(LICENSE_HEADER)
    new_content.append("\n")
    new_content.extend(remaining_lines)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_content)
    print(f"[+] Encabezado Apache 2.0 inyectado: {file_path}")

def main():
    print(f"[*] Iniciando auditoría de licenciamiento en: {TARGET_DIR}")
    for root, _, files in os.walk(TARGET_DIR):
        # Evitamos tocar entornos virtuales o bases de datos locales
        if ".venv" in root or ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py") and file != "apply_license.py":
                patch_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
