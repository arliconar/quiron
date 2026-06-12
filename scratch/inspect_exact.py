path = r"C:\Users\artzm\OneDrive\Documentos\GitHub\quiron\temp_page_26.txt"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's search for "de entre" and show it
idx = content.find("de entre")
if idx != -1:
    slice_chars = content[idx:idx+30]
    print("de entre exact repr:")
    print(repr(slice_chars))
    print([hex(ord(c)) for c in slice_chars])

# Let's search for "calibres mas"
idx = content.find("calibres mas")
if idx != -1:
    slice_chars = content[idx:idx+80]
    print("\ncalibres mas exact repr:")
    print(repr(slice_chars))
    print([hex(ord(c)) for c in slice_chars])

# Let's search for "debe de"
idx = content.find("debe de")
if idx != -1:
    slice_chars = content[idx:idx+25]
    print("\ndebe de exact repr:")
    print(repr(slice_chars))
    print([hex(ord(c)) for c in slice_chars])

# Let's search for "conexión"
idx = content.find("conexi\u00f3n")
if idx != -1:
    slice_chars = content[idx:idx+30]
    print("\nconexión exact repr:")
    print(repr(slice_chars))
    print([hex(ord(c)) for c in slice_chars])
