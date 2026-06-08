#!/usr/bin/env python3
"""
app/audit_archiver.py — GAP‑27 Audit Log Archival & Compression (Colab‑ready, FIXED v3)
"""
import json, os, hashlib, time, tempfile, gzip
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple

try:
    import zstandard as zstd
    _ZSTD_AVAILABLE = True
except ImportError:
    _ZSTD_AVAILABLE = False

def compress_data(data: bytes, algorithm: str = "zstd") -> bytes:
    if algorithm == "zstd" and _ZSTD_AVAILABLE:
        return zstd.ZstdCompressor().compress(data)
    return gzip.compress(data)

def decompress_data(data: bytes, algorithm: str = "zstd") -> bytes:
    if algorithm == "zstd" and _ZSTD_AVAILABLE:
        return zstd.ZstdDecompressor().decompress(data)
    return gzip.decompress(data)

class ArchiveRecord:
    def __init__(self, decision_id, bindings, result, timestamp, signature=""):
        self.decision_id = decision_id; self.bindings = bindings
        self.result = result; self.timestamp = timestamp; self.signature = signature
    def to_dict(self): return {"decision_id":self.decision_id,"bindings":self.bindings,
                                "result":self.result,"timestamp":self.timestamp,"signature":self.signature}

class ArchiveStore(ABC):
    @abstractmethod
    def upload_archive(self, key, data, metadata): ...
    @abstractmethod
    def download_archive(self, key) -> Tuple[bytes, dict]: ...
    @abstractmethod
    def delete_archive(self, key): ...

class LocalArchiveStore(ArchiveStore):
    def __init__(self, root_dir: str):
        self.root = root_dir
        os.makedirs(self.root, exist_ok=True)
    def upload_archive(self, key, data, metadata):
        fp = os.path.join(self.root, key)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "wb") as f: f.write(data)
        with open(fp + ".meta.json", "w") as f: json.dump(metadata, f)
        return fp
    def download_archive(self, key):
        fp = os.path.join(self.root, key)
        with open(fp, "rb") as f: data = f.read()
        meta = {}
        mp = fp + ".meta.json"
        if os.path.exists(mp):
            with open(mp) as f: meta = json.load(f)
        return data, meta
    def delete_archive(self, key):
        fp = os.path.join(self.root, key)
        for path in (fp, fp + ".meta.json"):
            if os.path.exists(path): os.remove(path)

class SimulatedPartitionStore:
    def __init__(self): self._data = {}
    def insert(self, pname, rec): self._data.setdefault(pname, []).append(rec)
    def get_partition(self, pname): return self._data.get(pname, [])
    def drop_partition(self, pname): self._data.pop(pname, None)
    def list_partitions(self, prefix=""): return sorted([k for k in self._data if k.startswith(prefix)])

class AuditLogPartitioner:
    def __init__(self, store): self.store = store
    def get_partition_name(self, tenant, ts):
        return f"audit_log_{ts.year}_{ts.month:02d}_{tenant}"
    def get_archiveable_partitions(self, tenant, cutoff):
        parts = []
        for pname in self.store.list_partitions():
            if not pname.startswith("audit_log_") or not pname.endswith(tenant): continue
            try:
                y, m = int(pname.split("_")[2]), int(pname.split("_")[3])
                # FIX: make parsed date timezone‑aware to match cutoff
                partition_date = datetime(y, m, 1, tzinfo=timezone.utc)
                if partition_date < cutoff.replace(day=1):
                    parts.append(pname)
            except: pass
        return parts

class ArchivalManager:
    def __init__(self, part_store, archive_store, partitioner, alg="zstd"):
        self.part_store = part_store; self.arch_store = archive_store
        self.partitioner = partitioner; self.alg = alg
    def archive_partition(self, pname, tenant):
        recs = self.part_store.get_partition(pname)
        if not recs: return {"status":"empty","partition":pname}
        arch = {"archive_id":f"archive-{pname}","tenant_id":tenant,"partition":pname,
                "record_count":len(recs),"records":[r.to_dict() for r in recs],
                "created_at":datetime.now(timezone.utc).isoformat(),"immutable":True}
        raw = json.dumps(arch, indent=2).encode()
        comp = compress_data(raw, self.alg)
        chk = hashlib.sha256(comp).hexdigest(); arch["checksum"] = chk
        key = f"warm/{tenant}/{pname}/{arch['archive_id']}.{'zst' if self.alg=='zstd' else 'gz'}"
        meta = {"checksum":chk,"immutable":"true","record_count":str(len(recs)),"compression":self.alg}
        self.arch_store.upload_archive(key, comp, meta)
        back, _ = self.arch_store.download_archive(key)
        if hashlib.sha256(back).hexdigest() != chk: raise RuntimeError("upload check fail")
        self.part_store.drop_partition(pname)
        return {"status":"archived","partition":pname,"s3_key":key,
                "record_count":len(recs),"compressed_size":len(comp),
                "original_size":len(raw),"checksum":chk}

class ArchivalRestorer:
    def __init__(self, part_store, arch_store):
        self.part_store = part_store; self.arch_store = arch_store
    def restore_partition(self, key, tenant):
        data, meta = self.arch_store.download_archive(key)
        if hashlib.sha256(data).hexdigest() != meta["checksum"]:
            raise RuntimeError("checksum mismatch")
        arch = json.loads(decompress_data(data))
        for r in arch["records"]:
            self.part_store.insert(arch["partition"], ArchiveRecord(**r))
        return len(arch["records"])

class RetentionManager:
    def __init__(self, arch_store, partitioner, default_days=365*7):
        self.arch_store = arch_store; self.partitioner = partitioner
        self.default_days = default_days; self.purge_log = []
    def purge_expired_archives(self, tenant, retention_days=None):
        if retention_days is None: retention_days = self.default_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        purged = []
        warm = os.path.join(self.arch_store.root, "warm", tenant)
        if not os.path.exists(warm): return purged
        for root, dirs, files in os.walk(warm):
            for fn in files:
                if fn.endswith((".zst",".gz")):
                    key = os.path.relpath(os.path.join(root, fn), self.arch_store.root)
                    _, meta = self.arch_store.download_archive(key)
                    created = meta.get("created_at","")
                    if created and datetime.fromisoformat(created) < cutoff:
                        self.arch_store.delete_archive(key)
                        e = {"key":key,"purged_at":datetime.now(timezone.utc).isoformat(),
                             "retention_days":retention_days}
                        purged.append(e); self.purge_log.append(e)
        return purged
