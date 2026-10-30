# Discord Bot — Python / Components V2

## ติดตั้ง

```bash
python -m pip install -r requirements.txt
```

คัดลอก `.env.example` เป็น `.env` ใส่ `DISCORD_TOKEN` และเปิด **Message Content Intent** ใน Discord Developer Portal

## เริ่มบอท

```bash
python bot.py
```

## ใช้งาน

แนบไฟล์ `.lua`, `.luau` หรือ `.txt` แล้วส่งคำสั่ง `.deobf` (เปลี่ยน prefix ได้จาก `PREFIX` ใน `.env`)

ระบบใช้คิวประมวลผล, จำกัดขนาดไฟล์, ตรวจจับ Obfuscator/เวอร์ชัน, แสดงสถานะ, และส่งไฟล์ผลลัพธ์กลับใน Discord Components V2 เมื่อใช้ discord.py รุ่นที่รองรับ หากโฮสต์ใช้รุ่นที่ไม่มี Components V2 จะ fallback เป็น Embed
