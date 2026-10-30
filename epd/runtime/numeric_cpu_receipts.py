"""Atomic, exclusive JSON receipts for the finite CPU diagnostic."""
import json
import os
from pathlib import Path


def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def publish(path,value):
    path=Path(path);pending=path.with_name(path.name+'.pending')
    if path.parent.is_symlink() or path.parent.stat().st_uid!=os.getuid():
        raise ValueError('Owned receipt directory required')
    fd=os.open(pending,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w',encoding='utf8') as out:
        json.dump(value,out);out.flush();os.fsync(out.fileno())
    # A pre-existing target (including a symlink) is never overwritten.
    os.link(pending,path,follow_symlinks=False)
    sync_directory(path.parent)
    pending.unlink();sync_directory(path.parent)
