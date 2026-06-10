#!/usr/bin/env python3
"""
app/constraint_sources.py — GAP‑38 External Constraint Source Integration
(CORRECTED v2)
"""
import json, time, re, hashlib, threading, logging, os, tempfile
from datetime import datetime, timedelta, timezone
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SourceStatus(Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class SourceHealthMetrics:
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.status = SourceStatus.UNKNOWN
        self.last_successful_fetch = None
        self.last_error = None
        self.error_count_24h = 0
        self.consecutive_failures = 0
        self.cache_hit_count = 0
        self.cache_miss_count = 0
        self.fetch_times = []
        self.constraint_count = 0
        self.last_update_detected = None
        self.created_at = datetime.now(timezone.utc)

    @property
    def cache_hit_rate_percent(self) -> float:
        total = self.cache_hit_count + self.cache_miss_count
        if total == 0:
            return 0.0
        return (self.cache_hit_count / total) * 100

    @property
    def avg_fetch_time_ms(self) -> float:
        if not self.fetch_times:
            return 0.0
        return sum(self.fetch_times[-100:]) / len(self.fetch_times[-100:])

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "status": self.status.value,
            "last_successful_fetch": self.last_successful_fetch.isoformat() if self.last_successful_fetch else None,
            "last_error": self.last_error,
            "error_count_24h": self.error_count_24h,
            "consecutive_failures": self.consecutive_failures,
            "cache_hit_rate_percent": self.cache_hit_rate_percent,
            "avg_fetch_time_ms": self.avg_fetch_time_ms,
            "constraint_count": self.constraint_count,
            "last_update_detected": self.last_update_detected.isoformat() if self.last_update_detected else None,
        }


class ValidationResult:
    def __init__(self, valid: bool, constraint_count: int, source_version: str = ""):
        self.valid = valid
        self.constraint_count = constraint_count
        self.source_version = source_version
        self.errors = []
        self.warnings = []
        self.timestamp = datetime.now(timezone.utc)

    def add_error(self, error: str):
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "constraint_count": self.constraint_count,
            "source_version": self.source_version,
            "timestamp": self.timestamp.isoformat(),
        }


class ConstraintSource(ABC):
    def __init__(self, source_name: str, source_config: dict):
        self.source_name = source_name
        self.config = source_config
        self.metrics = SourceHealthMetrics(source_name)

    @abstractmethod
    def fetch(self) -> Tuple[List[dict], bool]:
        pass

    @abstractmethod
    def has_updates(self, last_fetch_hash: str) -> bool:
        pass


class RESTAPISource(ConstraintSource):
    def fetch(self) -> Tuple[List[dict], bool]:
        start_time = time.time()
        try:
            import requests
            url = self.config.get("url")
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config.get('auth_token', '')}"
            }
            timeout = self.config.get("timeout_seconds", 15)
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code != 200:
                self.metrics.last_error = f"HTTP {response.status_code}"
                self.metrics.consecutive_failures += 1
                self.metrics.error_count_24h += 1
                return [], False
            data = response.json()
            constraints = data.get("constraints", [])
            if not isinstance(constraints, list):
                self.metrics.last_error = "Response constraints not a list"
                self.metrics.consecutive_failures += 1
                return [], False
            fetch_time = (time.time() - start_time) * 1000
            self.metrics.fetch_times.append(fetch_time)
            self.metrics.last_successful_fetch = datetime.now(timezone.utc)
            self.metrics.last_error = None
            self.metrics.consecutive_failures = 0
            self.metrics.constraint_count = len(constraints)
            self.metrics.status = SourceStatus.HEALTHY
            return constraints, True
        except Exception as e:
            self.metrics.last_error = str(e)
            self.metrics.consecutive_failures += 1
            self.metrics.error_count_24h += 1
            return [], False

    def has_updates(self, last_fetch_hash: str) -> bool:
        constraints, success = self.fetch()
        if not success:
            return False
        current_hash = hashlib.md5(json.dumps(constraints, sort_keys=True).encode()).hexdigest()
        return current_hash != last_fetch_hash


class DatabaseSource(ConstraintSource):
    def __init__(self, source_name: str, source_config: dict, db_connection=None):
        super().__init__(source_name, source_config)
        self.db = db_connection

    def fetch(self) -> Tuple[List[dict], bool]:
        start_time = time.time()
        try:
            query = self.config.get("query")
            timeout = self.config.get("timeout_seconds", 10)
            cursor = self.db.cursor()
            cursor.execute(query, timeout=timeout)
            rows = cursor.fetchall()
            constraints = []
            for row in rows:
                constraints.append({
                    "name": row[0],
                    "canonical_form": row[1],
                    "description": row[2] if len(row) > 2 else ""
                })
            fetch_time = (time.time() - start_time) * 1000
            self.metrics.fetch_times.append(fetch_time)
            self.metrics.last_successful_fetch = datetime.now(timezone.utc)
            self.metrics.last_error = None
            self.metrics.consecutive_failures = 0
            self.metrics.constraint_count = len(constraints)
            self.metrics.status = SourceStatus.HEALTHY
            return constraints, True
        except Exception as e:
            self.metrics.last_error = str(e)
            self.metrics.consecutive_failures += 1
            self.metrics.error_count_24h += 1
            return [], False

    def has_updates(self, last_fetch_hash: str) -> bool:
        constraints, success = self.fetch()
        if not success:
            return False
        current_hash = hashlib.md5(json.dumps(constraints, sort_keys=True).encode()).hexdigest()
        return current_hash != last_fetch_hash


class LocalFileSource(ConstraintSource):
    def fetch(self) -> Tuple[List[dict], bool]:
        start_time = time.time()
        try:
            file_path = self.config.get("file_path", "/app/constraints.json")
            with open(file_path, 'r') as f:
                data = json.load(f)
            constraints = data.get("constraints", [])
            fetch_time = (time.time() - start_time) * 1000
            self.metrics.fetch_times.append(fetch_time)
            self.metrics.last_successful_fetch = datetime.now(timezone.utc)
            self.metrics.last_error = None
            self.metrics.consecutive_failures = 0
            self.metrics.constraint_count = len(constraints)
            self.metrics.status = SourceStatus.HEALTHY
            return constraints, True
        except Exception as e:
            self.metrics.last_error = str(e)
            self.metrics.consecutive_failures += 1
            self.metrics.error_count_24h += 1
            return [], False

    def has_updates(self, last_fetch_hash: str) -> bool:
        try:
            file_path = self.config.get("file_path")
            with open(file_path, 'r') as f:
                data = json.load(f)
            constraints = data.get("constraints", [])
            current_hash = hashlib.md5(json.dumps(constraints, sort_keys=True).encode()).hexdigest()
            return current_hash != last_fetch_hash
        except:
            return False


class ConstraintValidator:
    def __init__(self, max_constraint_count: int = 1000, max_complexity: int = 256):
        self.max_constraint_count = max_constraint_count
        self.max_complexity = max_complexity

    def validate(self, constraints: List[dict], source_name: str, source_version: str = "") -> ValidationResult:
        result = ValidationResult(valid=True, constraint_count=len(constraints), source_version=source_version)
        if len(constraints) == 0:
            result.add_error("No constraints in source")
        elif len(constraints) > self.max_constraint_count:
            result.add_error(f"Constraint count ({len(constraints)}) exceeds max ({self.max_constraint_count})")
        seen_names = set()
        for i, constraint in enumerate(constraints):
            if not isinstance(constraint, dict):
                result.add_error(f"Constraint {i} is not a dict")
                continue
            name = constraint.get("name")
            canonical_form = constraint.get("canonical_form")
            if not name:
                result.add_error(f"Constraint {i} missing 'name' field")
                continue
            if not canonical_form:
                result.add_error(f"Constraint '{name}' missing 'canonical_form' field")
                continue
            if name in seen_names:
                result.add_error(f"Constraint '{name}' is duplicated")
            seen_names.add(name)
            if not self._is_valid_canonical_form(canonical_form):
                result.add_error(f"Constraint '{name}' invalid canonical_form: '{canonical_form}'")
            complexity = len(canonical_form.split())
            if complexity > self.max_complexity:
                result.add_error(f"Constraint '{name}' too complex ({complexity} > {self.max_complexity})")
            effective_date = constraint.get("effective_date")
            if effective_date:
                try:
                    ed = datetime.fromisoformat(effective_date)
                    if ed > datetime.now(timezone.utc):
                        result.add_warning(f"Constraint '{name}' effective_date is in future ({effective_date})")
                except:
                    result.add_error(f"Constraint '{name}' invalid effective_date: {effective_date}")
        return result

    def _is_valid_canonical_form(self, cf: str) -> bool:
        pattern = r'^\s*(\w+)\s*(>=|<=|>|<|==|!=)\s*(-?\d+(?:\.\d+)?)\s*$'
        return re.match(pattern, cf.strip()) is not None


class SourceCache:
    def __init__(self, default_ttl_seconds: int = 3600):
        self.cache = {}
        self.default_ttl = default_ttl_seconds
        self.locks = defaultdict(threading.Lock)

    def get(self, source_name: str, tenant_id: str) -> Optional[List[dict]]:
        key = (source_name, tenant_id)
        if key not in self.cache:
            return None
        constraints, expire_time = self.cache[key]
        if datetime.now(timezone.utc) > expire_time:
            del self.cache[key]
            return None
        return constraints

    def set(self, source_name: str, tenant_id: str, constraints: List[dict], ttl_seconds: int = None):
        # FIXED: was `ttl = ttl_seconds or self.default_ttl` which treated 0 as falsy
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        key = (source_name, tenant_id)
        expire_time = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self.cache[key] = (constraints, expire_time)

    def invalidate(self, source_name: str, tenant_id: str = None):
        if tenant_id:
            self.cache.pop((source_name, tenant_id), None)
        else:
            keys_to_delete = [k for k in self.cache.keys() if k[0] == source_name]
            for key in keys_to_delete:
                del self.cache[key]

    def clear_all(self):
        self.cache.clear()


class ConstraintSourceManager:
    def __init__(self):
        self.sources: Dict[str, ConstraintSource] = {}
        self.cache = SourceCache()
        self.validator = ConstraintValidator()
        self.last_known_good = {}
        self.config = {}

    def register_source(self, source_config: dict, db_connection=None):
        source_name = source_config.get("name")
        source_type = source_config.get("type", "local_file")
        if source_type == "rest_api":
            source = RESTAPISource(source_name, source_config)
        elif source_type == "database":
            source = DatabaseSource(source_name, source_config, db_connection)
        elif source_type == "local_file":
            source = LocalFileSource(source_name, source_config)
        else:
            raise ValueError(f"Unknown source type: {source_type}")
        self.sources[source_name] = source
        self.config[source_name] = source_config

    def get_constraints(self, tenant_id: str, source_name: str) -> List[dict]:
        # FIXED: guard against non-existent source before accessing metrics
        if source_name not in self.sources:
            return []
        cached = self.cache.get(source_name, tenant_id)
        if cached:
            self.sources[source_name].metrics.cache_hit_count += 1
            return cached
        self.sources[source_name].metrics.cache_miss_count += 1
        source = self.sources[source_name]
        constraints, success = source.fetch()
        if not success:
            fallback_source = self.config[source_name].get("fallback_source")
            if fallback_source:
                return self.get_constraints(tenant_id, fallback_source)
            lkg_key = (source_name, tenant_id)
            if lkg_key in self.last_known_good:
                return self.last_known_good[lkg_key]
            return []
        validation = self.validator.validate(constraints, source_name)
        if not validation.valid:
            lkg_key = (source_name, tenant_id)
            if lkg_key in self.last_known_good:
                return self.last_known_good[lkg_key]
            return []
        ttl = self.config[source_name].get("cache_ttl_seconds", 3600)
        self.cache.set(source_name, tenant_id, constraints, ttl)
        self.last_known_good[(source_name, tenant_id)] = constraints
        return constraints

    def get_constraints_composed(self, tenant_id: str, source_names: List[str]) -> List[dict]:
        composed = {}
        for source_name in source_names:
            source_config = self.config.get(source_name, {})
            priority = source_config.get("priority", 999)
            constraints = self.get_constraints(tenant_id, source_name)
            for constraint in constraints:
                name = constraint.get("name")
                if name not in composed:
                    composed[name] = (constraint, priority)
                else:
                    existing_constraint, existing_priority = composed[name]
                    if priority < existing_priority:
                        composed[name] = (constraint, priority)
        return [c for c, _ in composed.values()]

    def get_source_status(self, source_name: str) -> Dict[str, Any]:
        source = self.sources.get(source_name)
        if not source:
            return {"error": f"Source '{source_name}' not found"}
        return source.metrics.to_dict()

    def invalidate_cache(self, source_name: str, tenant_id: str = None):
        self.cache.invalidate(source_name, tenant_id)

    def get_all_source_statuses(self) -> Dict[str, Dict[str, Any]]:
        return {name: self.get_source_status(name) for name in self.sources.keys()}
