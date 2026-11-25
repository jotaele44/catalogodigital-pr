"""Bounded local migration backup and restore. No overwrite of existing files."""
import hashlib
import os
import sqlite3
from pathlib import Path
from .schema_v3 import configure, validate_v2, legacy_snapshot

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def reserve(path):
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    os.close(fd)

def backup_v2(source,destination):
    source,destination=Path(source).resolve(),Path(destination).absolute()
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    created=False
    try:
        configure(src)
        src.execute('BEGIN')
        validate_v2(src)
        before=legacy_snapshot(src)
        reserve(destination); created=True
        dst=sqlite3.connect(destination)
        try: src.backup(dst)
        finally: dst.close()
        check=sqlite3.connect(destination.resolve().as_uri()+'?mode=ro',uri=True)
        try:
            configure(check); validate_v2(check)
            if legacy_snapshot(check)!=before: raise ValueError('backup conservation failure')
        finally: check.close()
        with open(destination,'rb') as f: os.fsync(f.fileno())
        return {'sha256':digest(destination),'byte_count':destination.stat().st_size,'schema_version':2}
    except Exception:
        if created: destination.unlink(missing_ok=True)
        raise
    finally: src.close()

def restore_v2(backup,destination,receipt):
    backup,destination=Path(backup).resolve(),Path(destination).absolute()
    if receipt.get('schema_version')!=2 or digest(backup)!=receipt.get('sha256') or backup.stat().st_size!=receipt.get('byte_count'):
        raise ValueError('backup receipt mismatch')
    reserve(destination)
    try:
        with open(backup,'rb') as src, open(destination,'wb') as dst:
            for chunk in iter(lambda:src.read(1024*1024),b''): dst.write(chunk)
            dst.flush(); os.fsync(dst.fileno())
        if digest(destination)!=receipt['sha256']: raise ValueError('restore digest mismatch')
        db=sqlite3.connect(destination.resolve().as_uri()+'?mode=ro',uri=True)
        try: configure(db); validate_v2(db)
        finally: db.close()
    except Exception:
        destination.unlink(missing_ok=True)
        raise

