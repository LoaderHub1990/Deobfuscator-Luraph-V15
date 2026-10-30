# Flexozy Luraph Deobfuscator — Python edition

โค้ดควบคุมโปรเจกต์และ Discord Bot ใช้ Python ทั้งหมด ไม่มี Node.js / npm / JavaScript entrypoint

## ติดตั้ง

```bash
python -m pip install -r requirements.txt
```

ตั้งค่า `.env` จาก `.env.example` แล้วใส่ `DISCORD_TOKEN` ของบอท จากนั้นเปิด **Message Content Intent** ใน Discord Developer Portal

## เปิด Discord Bot

```bash
python bot.py
```

คำสั่งเดิม: แนบไฟล์ `.lua`, `.luau` หรือ `.txt` แล้วส่ง `.deobf`

## ใช้ตัว Deobfuscator ผ่าน CLI

```bash
python deob.py input.lua
python deob.py input.lua -o output.lua
python deob.py input.lua --detect
python deob.py input.lua --no-devirt
python deob.py ./scripts --jobs 4
```

ตัวเลือกหลักยังคงเดิม: `--timeout`, `--budget`, `--max-runs`, `--devirt-rounds`, `--no-hooks`, `--no-fold`, `--strings`, `--debug`, `--keep-harness`, `--keep-preamble` และ `--executor`

## ดาวน์โหลดสคริปต์จาก URL

```bash
python fetch.py https://example.com/script.lua
python fetch.py https://example.com/script.lua -o downloaded.lua
```

## Runtime ที่จำเป็น

ตัววิเคราะห์หลัก, CLI, Discord Bot, ตัวดึงไฟล์, orchestration, AST analysis และ devirtualization ใช้ Python แล้ว แต่การจำลองพฤติกรรม Luau ยังต้องมี executable `luau` และ `luau-ast` ที่คอมไพล์ตรงกับระบบปฏิบัติการของโฮสต์อยู่ใน `bin/` หรือ PATH (Windows ใช้ `.exe`; Linux ใช้ไฟล์ Linux ไม่มีนามสกุล) เพราะตัว Luau เป็น runtime/compiler แยกจากภาษา Python

ZIP ต้นฉบับมี binary สำหรับ Windows เท่านั้น หากโฮสต์เป็น Linux ต้องนำ binary Linux ที่เข้ากันได้มาใส่ `bin/` ก่อนรันงานจริง

## ข้อจำกัดการรองรับ

- Luraph v15 เป็นเส้นทางหลัก
- Luraph v14.7–v14.9 ยังเป็น experimental ตามข้อจำกัดของตัว lifter เดิม
- ผลลัพธ์ขึ้นกับรูปแบบ VM และความสามารถในการรันสคริปต์ใน offline Luau runtime
- อย่ารันสคริปต์ที่ไม่น่าเชื่อถือบนเครื่องที่มีข้อมูลสำคัญ ควรแยก process/container และจำกัด CPU/RAM
