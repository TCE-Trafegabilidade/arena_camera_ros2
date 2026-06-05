import arena_api.system as system

devices = system.create_device()
device = devices[0]
nm = device.nodemap

for name in [
    "DeviceVendorName",
    "DeviceModelName",
    "DeviceSerialNumber",
    "Width",
    "Height",
    "PixelFormat",
    "ExposureTime",
]:
    print(f"\n=== {name} ===")
    try:
        node = nm.get_node(name) if hasattr(nm, "get_node") else nm[name]
        print("type(node):", type(node))
        print("dir snippet:", [x for x in dir(node) if not x.startswith("_")][:30])

        for attr in ["value", "is_readable", "is_writable", "min", "max", "inc", "unit"]:
            try:
                print(attr, "=>", getattr(node, attr))
            except Exception as e:
                print(attr, "=> ERRO", repr(e))

        for method in ["get_value", "to_string"]:
            try:
                if hasattr(node, method):
                    print(method, "=>", getattr(node, method)())
            except Exception as e:
                print(method, "=> ERRO", repr(e))

    except Exception as e:
        print("Falha ao obter node:", repr(e))
