import re, sys

rupee  = chr(0x20b9)   # Indian Rupee sign: Rs.
euro   = chr(0x20ac)   # Euro sign: EUR
pound  = chr(0x00a3)   # Pound sign: GBP

NEW_FUNC = (
    "def sanitize_currency_symbol(sym: str) -> str:\n"
    "    '''\n"
    "    Converts raw unicode currency symbols to ReportLab-safe ASCII equivalents.\n"
    "    Standard ReportLab built-in fonts (Helvetica, Times-Roman) only cover\n"
    "    Latin-1/WinAnsi and cannot render the Rupee, Euro, or Pound glyphs -\n"
    "    they appear as solid black boxes. This maps them to ASCII strings.\n"
    "    '''\n"
    "    if not sym:\n"
    "        return chr(36)\n"
    "    sym = sym.strip()\n"
    "    mapping = {\n"
    "        chr(0x20b9): 'Rs.',\n"
    "        'INR': 'Rs.',\n"
    "        chr(36): chr(36),\n"
    "        'USD': chr(36),\n"
    "        chr(0x20ac): 'EUR',\n"
    "        'EUR': 'EUR',\n"
    "        chr(0x00a3): 'GBP',\n"
    "        'GBP': 'GBP',\n"
    "    }\n"
    "    return mapping.get(sym, sym)"
)

with open("pdf_generator.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the broken function body
old_block_start = "def sanitize_currency_symbol(sym: str) -> str:"
assert old_block_start in content

# Use regex to replace from def ... to the blank line after return
content = re.sub(
    r"def sanitize_currency_symbol\(sym: str\) -> str:.*?return mapping\.get\(sym, sym\)",
    NEW_FUNC,
    content,
    flags=re.DOTALL
)

with open("pdf_generator.py", "w", encoding="utf-8") as f:
    f.write(content)

print("pdf_generator.py patched!")
