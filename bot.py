#!/usr/bin/env python3
"""Discord Components V2 bot wrapper. Entire application layer is Python."""
from __future__ import annotations
import asyncio, os, re, tempfile, traceback
from pathlib import Path
from urllib.request import Request, urlopen
import discord
from dotenv import load_dotenv
from deob import detect

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
TOKEN = os.getenv('DISCORD_TOKEN', '').strip()
PREFIX = os.getenv('PREFIX', '.')
COMMAND = f'{PREFIX}deobf'
MAX_FILE_MB = max(1, int(os.getenv('MAX_FILE_MB', '8')))
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
JOB_TIMEOUT = max(60, int(os.getenv('JOB_TIMEOUT_MS', '1200000')) / 1000)
LUAU_TIMEOUT = max(90, int(os.getenv('LUAU_TIMEOUT', '900')))
LUAU_BUDGET = max(30, int(os.getenv('LUAU_BUDGET', '300')))
ALLOWED = {'.lua', '.luau', '.txt'}
LOADING = '<a:loading:1562187564230905917>'
SUCCESS = '<:success:1564257560792535140>'

if not TOKEN:
    raise SystemExit('[BOT] Missing DISCORD_TOKEN in .env')

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
client = discord.Client(intents=intents)
queue_lock = asyncio.Lock()
active_users: set[int] = set()

def status_view(title: str, body: str, color: int = 0x5865F2):
    """Use native Components V2 when supported by installed discord.py."""
    try:
        layout = discord.ui.LayoutView(timeout=None)
        box = discord.ui.Container(accent_colour=discord.Colour(color))
        box.add_item(discord.ui.TextDisplay(content=f'# {title}\n{body}'))
        layout.add_item(box)
        return layout
    except (AttributeError, TypeError):
        return None

def status_embed(title: str, body: str, color: int = 0x5865F2):
    e = discord.Embed(title=title, description=body, colour=color)
    return e

async def send_status(message, title, body, color=0x5865F2, *, edit=None, file=None):
    view = status_view(title, body, color)

    if edit is not None:
        if view is not None:
            await edit.edit(
                content=None,
                embed=None,
                view=view
            )
        else:
            await edit.edit(
                embed=status_embed(title, body, color),
                view=None
            )

        if file is not None:
            await message.reply(
                file=file,
                mention_author=False
            )

        return edit

    if view is not None:
        status_message = await message.reply(
            view=view,
            mention_author=False
        )
    else:
        status_message = await message.reply(
            embed=status_embed(title, body, color),
            mention_author=False
        )

    if file is not None:
        await message.reply(
            file=file,
            mention_author=False
        )

    return status_message

def safe_name(name: str) -> str:
    name = Path(name or 'input.lua').name
    return re.sub(r'[^\w.\- ()]', '_', name, flags=re.UNICODE)[:100] or 'input.lua'

def download_attachment(url: str, destination: Path):
    req = Request(url, headers={'User-Agent': 'Flexozy-Deobfuscator/2.0'})
    with urlopen(req, timeout=45) as response:
        data = response.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f'ไฟล์มีขนาดเกิน {MAX_FILE_MB} MB')
    if not data:
        raise ValueError('ไฟล์ว่างเปล่า')
    destination.write_bytes(data)

def detect_version(source: str):
    plugin, confidence = detect(source)
    header = re.search(r'This file was protected using Luraph Obfuscator v([\d.]+)', source[:600], re.I)
    if header:
        version = f'v{header.group(1)}'
    elif plugin.name == 'luraph_v15':
        version = 'v15 (ตรวจจากรูปแบบ VM)'
    elif plugin.name == 'luraph_v14':
        version = 'v14.x (ตรวจจากรูปแบบ VM)'
    else:
        version = 'ไม่สามารถระบุเวอร์ชันได้'
    return plugin.label, version, f'{round(confidence * 100)}%' if confidence else 'ไม่พบลายเซ็นที่รองรับ'

async def run_engine(input_path: Path, output_path: Path):
    cmd = [os.getenv('PYTHON_BIN', 'python'), str(ROOT / 'deob.py'), str(input_path), '-o', str(output_path),
           '--timeout', str(LUAU_TIMEOUT), '--budget', str(LUAU_BUDGET)]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, cwd=ROOT, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, env=os.environ.copy())
    except FileNotFoundError:
        # Linux hosts commonly expose python3 rather than python.
        cmd[0] = 'python3'
        proc = await asyncio.create_subprocess_exec(*cmd, cwd=ROOT, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, env=os.environ.copy())
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=JOB_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill(); await proc.communicate()
        raise TimeoutError('หมดเวลาประมวลผล งานนี้ใช้เวลานานเกินกำหนด')
    if proc.returncode != 0 or not output_path.exists():
        detail = (stderr or stdout).decode('utf-8', 'replace').strip()[-1400:]
        raise RuntimeError(detail or f'Engine exited with code {proc.returncode}')
    if output_path.stat().st_size == 0:
        raise RuntimeError('Engine สร้างไฟล์ผลลัพธ์ว่าง')

async def process_message(message, attachment):
    uid = message.author.id
    if uid in active_users:
        await send_status(message, 'กำลังประมวลผลอยู่', 'คุณมีงานที่กำลังทำงานอยู่ กรุณารอให้งานเดิมเสร็จก่อน', 0xF0B232)
        return
    ext = Path(attachment.filename).suffix.lower()
    if ext not in ALLOWED:
        return
    if attachment.size > MAX_FILE_BYTES:
        await send_status(message, 'ไฟล์ใหญ่เกินกำหนด', f'รองรับไฟล์ไม่เกิน {MAX_FILE_MB} MB', 0xED4245)
        return
    active_users.add(uid)
    status = await send_status(message, 'กำลังตรวจสอบไฟล์', f'{LOADING} รับไฟล์แล้ว กำลังตรวจสอบ Obfuscator และเวอร์ชัน...')
    async with queue_lock:
        temp_dir = Path(tempfile.mkdtemp(prefix='discord_deobf_'))
        name = safe_name(attachment.filename)
        input_path = temp_dir / f'input{ext}'
        output_path = temp_dir / 'result.deobf.luau'
        try:
            await asyncio.to_thread(download_attachment, attachment.url, input_path)
            source = input_path.read_bytes().decode('latin-1')
            obf, version, confidence = detect_version(source)
            await send_status(message, 'กำลังประมวลผล',
                f'{LOADING} **ไฟล์:** `{name}`\n**Obfuscator:** {obf}\n**เวอร์ชัน:** {version}\n**ความมั่นใจ:** {confidence}\n\nระบบกำลังวิเคราะห์และถอดโครงสร้างโค้ด กรุณารอ...', edit=status)
            await run_engine(input_path, output_path)
            size = output_path.stat().st_size
            with discord.File(
                output_path,
                filename=f'{Path(name).stem}.deobf.luau'
            ) as result_file:

                await send_status(
                    message,
                    'ประมวลผลสำเร็จ',
                    f'{SUCCESS} **ถอดโครงสร้างเสร็จแล้ว**\n'
                    f'**ไฟล์ต้นฉบับ:** `{name}`\n'
                    f'**Obfuscator:** {obf}\n'
                    f'**เวอร์ชัน:** {version}\n'
                    f'**ขนาดผลลัพธ์:** {size / 1024:.1f} KB\n\n'
                    'แนบไฟล์ผลลัพธ์ไว้ด้านล่างแล้ว',
                    0x57F287,
                    edit=status,
                    file=result_file
                )
        except Exception as exc:
            print('[DEOBF ERROR]', repr(exc))
            await send_status(message, 'ประมวลผลไม่สำเร็จ',
                f'❌ ไม่สามารถถอดไฟล์นี้ได้\n```\n{str(exc)[:1200]}\n```\nไฟล์หรือเวอร์ชันนี้อาจไม่รองรับ หรือระบบรันไทม์ยังตั้งค่าไม่ครบ',
                0xED4245, edit=status)
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            active_users.discard(uid)

@client.event
async def on_ready():
    print(f'[BOT] Logged in as {client.user}')
    print(f'[BOT] Command: {COMMAND} | Max file: {MAX_FILE_MB} MB')

@client.event
async def on_message(message):
    if message.author.bot or not message.content.strip().lower().startswith(COMMAND.lower()):
        return
    attachment = next((a for a in message.attachments if Path(a.filename).suffix.lower() in ALLOWED), None)
    if attachment is None:
        await send_status(message, 'Flexozy Deobfuscator', f'แนบไฟล์ `.lua`, `.luau` หรือ `.txt` พร้อมคำสั่ง `{COMMAND}`', 0xF0B232)
        return
    await process_message(message, attachment)

client.run(TOKEN)