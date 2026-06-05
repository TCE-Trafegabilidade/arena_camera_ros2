#!/usr/bin/env python3
"""
Exporta todos os nodes/metadados possíveis de uma câmera LUCID (Arena SDK) para JSON.

O script tenta ler:
- Device NodeMap
- TLDevice NodeMap (quando disponível)
- TLStream NodeMap (quando disponível)

Saída:
- JSON com infos do dispositivo
- lista de nodes com tipo, acesso, valor atual, min/max/inc, unidade, descrição, opções de enum etc.

Uso:
    python export_arena_nodes.py
    python export_arena_nodes.py --output camera_dump.json
    python export_arena_nodes.py --device-index 0 --pretty

Observações:
- Os nomes exatos de classes/métodos podem variar um pouco entre versões do Arena SDK.
- O script foi escrito para ser tolerante a diferenças de API e falhas de leitura.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Arena SDK (Python)
try:
    import arena_api.system as arena_system
except Exception as e:
    print("Erro ao importar arena_api.system. Verifique se o Arena SDK Python está instalado.", file=sys.stderr)
    raise


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return default


def try_call(obj: Any, method_name: str, *args, **kwargs) -> Any:
    try:
        method = getattr(obj, method_name)
        return method(*args, **kwargs)
    except Exception:
        return None


def json_safe(value: Any) -> Any:
    """Converte valores para algo serializável em JSON."""
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def node_display_name(node: Any) -> Optional[str]:
    for attr in ("display_name", "displayName", "DisplayName"):
        value = safe_getattr(node, attr)
        if value is not None:
            return str(value)
    return None


def node_description(node: Any) -> Optional[str]:
    for attr in ("description", "tool_tip", "tooltip", "ToolTip", "Description"):
        value = safe_getattr(node, attr)
        if value is not None:
            return str(value)
    return None


def node_visibility(node: Any) -> Optional[str]:
    for attr in ("visibility", "Visibility"):
        value = safe_getattr(node, attr)
        if value is not None:
            return str(value)
    return None


def node_unit(node: Any) -> Optional[str]:
    for attr in ("unit", "Unit"):
        value = safe_getattr(node, attr)
        if value is not None:
            return str(value)
    return None


def node_representation(node: Any) -> Optional[str]:
    for attr in ("representation", "Representation"):
        value = safe_getattr(node, attr)
        if value is not None:
            return str(value)
    return None


def node_interface_type(node: Any) -> str:
    for attr in ("interface_type", "interfaceType", "node_type", "principal_interface_type"):
        value = safe_getattr(node, attr)
        if value is not None:
            return str(value)
    # fallback
    return type(node).__name__


def node_access(node: Any) -> Dict[str, Optional[bool]]:
    readable = None
    writable = None
    implemented = None
    available = None

    for attr in ("is_readable", "readable", "IsReadable"):
        value = safe_getattr(node, attr)
        if value is not None:
            readable = bool(value)
            break

    for attr in ("is_writable", "writable", "IsWritable"):
        value = safe_getattr(node, attr)
        if value is not None:
            writable = bool(value)
            break

    for attr in ("is_implemented", "implemented", "IsImplemented"):
        value = safe_getattr(node, attr)
        if value is not None:
            implemented = bool(value)
            break

    for attr in ("is_available", "available", "IsAvailable"):
        value = safe_getattr(node, attr)
        if value is not None:
            available = bool(value)
            break

    return {
        "readable": readable,
        "writable": writable,
        "implemented": implemented,
        "available": available,
    }


def read_node_value(node: Any) -> Any:
    # Tenta ler o valor atual por diferentes caminhos.
    for attr in ("value", "Value"):
        try:
            return json_safe(getattr(node, attr))
        except Exception:
            pass

    for method_name in ("get_value", "GetValue", "to_string", "ToString"):
        result = try_call(node, method_name)
        if result is not None:
            return json_safe(result)

    # Para command nodes, não há "valor"
    return None


def read_numeric_limits(node: Any) -> Dict[str, Any]:
    data = {"min": None, "max": None, "inc": None}
    for key, attrs in {
        "min": ("min", "Min"),
        "max": ("max", "Max"),
        "inc": ("inc", "increment", "Inc", "Increment"),
    }.items():
        for attr in attrs:
            try:
                value = getattr(node, attr)
                data[key] = json_safe(value)
                break
            except Exception:
                pass
    return data


def read_string_limits(node: Any) -> Dict[str, Any]:
    data = {"max_length": None}
    for attr in ("max_length", "MaxLength"):
        try:
            data["max_length"] = json_safe(getattr(node, attr))
            break
        except Exception:
            pass
    return data


def read_enum_choices(node: Any) -> List[Dict[str, Any]]:
    choices: List[Dict[str, Any]] = []

    entries = safe_getattr(node, "entries")
    if entries is None:
        entries = try_call(node, "get_entries")
    if entries is None:
        return choices

    for entry in entries:
        entry_name = safe_getattr(entry, "name")
        if entry_name is None:
            entry_name = safe_getattr(entry, "symbolic")
        if entry_name is None:
            entry_name = str(entry)

        entry_data = {
            "name": str(entry_name),
            "display_name": node_display_name(entry),
            "description": node_description(entry),
            "value": None,
            "available": None,
            "readable": None,
        }

        for attr in ("value", "Value"):
            try:
                entry_data["value"] = json_safe(getattr(entry, attr))
                break
            except Exception:
                pass

        for attr in ("is_available", "available", "IsAvailable"):
            value = safe_getattr(entry, attr)
            if value is not None:
                entry_data["available"] = bool(value)
                break

        for attr in ("is_readable", "readable", "IsReadable"):
            value = safe_getattr(entry, attr)
            if value is not None:
                entry_data["readable"] = bool(value)
                break

        choices.append(entry_data)

    return choices


def read_category_children(node: Any) -> List[str]:
    features: List[str] = []
    for attr in ("features", "Features"):
        children = safe_getattr(node, attr)
        if children is not None:
            for child in children:
                child_name = safe_getattr(child, "name", str(child))
                features.append(str(child_name))
            return features

    for method_name in ("get_features", "GetFeatures"):
        children = try_call(node, method_name)
        if children is not None:
            for child in children:
                child_name = safe_getattr(child, "name", str(child))
                features.append(str(child_name))
            return features
    return features


def classify_node(node: Any) -> str:
    interface_type = node_interface_type(node).lower()

    if "enum" in interface_type:
        return "enumeration"
    if "float" in interface_type:
        return "float"
    if "int" in interface_type or "integer" in interface_type:
        return "integer"
    if "bool" in interface_type:
        return "boolean"
    if "string" in interface_type:
        return "string"
    if "command" in interface_type:
        return "command"
    if "category" in interface_type:
        return "category"
    if "register" in interface_type:
        return "register"
    return interface_type


def extract_node(node: Any, nodemap_name: str) -> Dict[str, Any]:
    name = str(safe_getattr(node, "name", "<unknown>"))
    interface_type = node_interface_type(node)
    kind = classify_node(node)
    access = node_access(node)

    result: Dict[str, Any] = {
        "nodemap": nodemap_name,
        "name": name,
        "display_name": node_display_name(node),
        "description": node_description(node),
        "interface_type": interface_type,
        "kind": kind,
        "visibility": node_visibility(node),
        "unit": node_unit(node),
        "representation": node_representation(node),
        "access": access,
        "value": None,
        "min": None,
        "max": None,
        "inc": None,
        "max_length": None,
        "enum_choices": [],
        "category_features": [],
        "errors": [],
    }

    # valor atual
    if access["readable"] is not False:
        try:
            result["value"] = read_node_value(node)
        except Exception as e:
            result["errors"].append(f"value_read_error: {e!r}")

    # limites
    if kind in ("integer", "float"):
        try:
            limits = read_numeric_limits(node)
            result.update(limits)
        except Exception as e:
            result["errors"].append(f"numeric_limits_error: {e!r}")

    if kind == "string":
        try:
            result.update(read_string_limits(node))
        except Exception as e:
            result["errors"].append(f"string_limits_error: {e!r}")

    if kind == "enumeration":
        try:
            result["enum_choices"] = read_enum_choices(node)
        except Exception as e:
            result["errors"].append(f"enum_choices_error: {e!r}")

    if kind == "category":
        try:
            result["category_features"] = read_category_children(node)
        except Exception as e:
            result["errors"].append(f"category_children_error: {e!r}")

    return result


def get_all_nodes(nodemap: Any) -> List[Any]:
    # Tenta múltiplas formas de obter todos os nodes
    for attr in ("nodes",):
        value = safe_getattr(nodemap, attr)
        if value is not None:
            try:
                return list(value)
            except Exception:
                pass

    for method_name in ("get_nodes", "GetNodes"):
        value = try_call(nodemap, method_name)
        if value is not None:
            try:
                return list(value)
            except Exception:
                pass

    # Fallback: impossível enumerar
    return []


def extract_nodemap(nodemap: Any, nodemap_name: str) -> Dict[str, Any]:
    nodes = get_all_nodes(nodemap)
    extracted_nodes: List[Dict[str, Any]] = []
    errors: List[str] = []

    for node in nodes:
        try:
            extracted_nodes.append(extract_node(node, nodemap_name))
        except Exception as e:
            node_name = safe_getattr(node, "name", "<unknown>")
            errors.append(f"{node_name}: {e!r}")

    return {
        "name": nodemap_name,
        "node_count": len(extracted_nodes),
        "errors": errors,
        "nodes": extracted_nodes,
    }


def get_device_identifier(device: Any) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "model": None,
        "vendor": None,
        "serial": None,
        "display_name": None,
        "device_version": None,
        "user_defined_name": None,
    }

    # tenta via device.info / tl nodemap / atributos diretos
    for attr in ("info",):
        device_info = safe_getattr(device, attr)
        if device_info is not None:
            for key in list(info.keys()):
                value = safe_getattr(device_info, key)
                if value is not None:
                    info[key] = str(value)

    # fallback em atributos diretos
    fallback_map = {
        "model": ("model", "model_name", "ModelName"),
        "vendor": ("vendor", "vendor_name", "VendorName"),
        "serial": ("serial", "serial_number", "SerialNumber"),
        "display_name": ("display_name", "DisplayName"),
        "device_version": ("device_version", "DeviceVersion"),
        "user_defined_name": ("user_defined_name", "UserDefinedName"),
    }
    for key, attrs in fallback_map.items():
        if info[key] is not None:
            continue
        for attr in attrs:
            value = safe_getattr(device, attr)
            if value is not None:
                info[key] = str(value)
                break

    return info


def maybe_get_nodemap(device: Any, names: List[str]) -> Any:
    for name in names:
        value = safe_getattr(device, name)
        if value is not None:
            return value
    return None


def build_export(device: Any, device_index: int) -> Dict[str, Any]:
    export: Dict[str, Any] = {
        "exported_at_utc": utc_now_iso(),
        "device_index": device_index,
        "device_info": get_device_identifier(device),
        "sdk": {
            "module": "arena_api.system",
        },
        "nodemaps": [],
        "notes": [
            "Nem todos os nodes estarão legíveis/escrevíveis em todos os estados da câmera.",
            "Alguns nodes dependem de TriggerMode, AcquisitionStop ou permissões de acesso.",
            "Diferenças entre firmware/modelo podem alterar nomes, ranges e disponibilidade.",
        ],
    }

    nodemap_candidates = [
        ("device", ["nodemap", "node_map"]),
        ("tl_device", ["tl_device_nodemap", "tl_dev_nodemap", "tl_nodemap_device"]),
        ("tl_stream", ["stream_nodemap", "tl_stream_nodemap", "tl_nodemap_stream"]),
    ]

    for nodemap_name, attr_names in nodemap_candidates:
        nodemap = maybe_get_nodemap(device, attr_names)
        if nodemap is not None:
            export["nodemaps"].append(extract_nodemap(nodemap, nodemap_name))

    return export


def connect_devices():
    # Compatibilidade: algumas versões usam system.create_device(); outras exigem objeto System.
    if hasattr(arena_system, "create_device"):
        return arena_system.create_device()

    sys_obj = None
    for getter in ("system", "System"):
        sys_obj = safe_getattr(arena_system, getter)
        if sys_obj is not None:
            break

    if sys_obj is None:
        raise RuntimeError("Não foi possível encontrar função de criação de devices no módulo arena_api.system")

    if callable(sys_obj):
        sys_obj = sys_obj()

    for method_name in ("create_device", "CreateDevice", "create_devices"):
        method = safe_getattr(sys_obj, method_name)
        if callable(method):
            return method()

    raise RuntimeError("Não foi possível criar devices com a API disponível.")


def destroy_devices(devices):
    # Algumas versões expõem arena_system.destroy_device(devices)
    destroy = safe_getattr(arena_system, "destroy_device")
    if callable(destroy):
        try:
            destroy(devices)
            return
        except Exception:
            pass

    # fallback sem destruir explicitamente
    return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporta nodes/metadados do Arena SDK para JSON.")
    parser.add_argument("--device-index", type=int, default=0, help="Índice da câmera a usar.")
    parser.add_argument("--output", default="arena_camera_dump.json", help="Arquivo de saída JSON.")
    parser.add_argument("--pretty", action="store_true", help="Formata JSON com indentação.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    devices = []
    try:
        devices = connect_devices()
        if not devices:
            print("Nenhuma câmera encontrada.", file=sys.stderr)
            return 2

        if args.device_index < 0 or args.device_index >= len(devices):
            print(
                f"device-index inválido: {args.device_index}. "
                f"Foram encontradas {len(devices)} câmeras.",
                file=sys.stderr,
            )
            return 2

        device = devices[args.device_index]
        payload = build_export(device, args.device_index)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(
                payload,
                f,
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            )

        # Resumo no terminal
        print(f"Arquivo gerado: {args.output}")
        print(f"Câmera: {payload['device_info']}")
        for nm in payload["nodemaps"]:
            print(f"- {nm['name']}: {nm['node_count']} nodes")

        return 0

    except Exception as e:
        print("Falha ao exportar nodes.", file=sys.stderr)
        print(repr(e), file=sys.stderr)
        traceback.print_exc()
        return 1

    finally:
        if devices:
            destroy_devices(devices)


if __name__ == "__main__":
    raise SystemExit(main())
