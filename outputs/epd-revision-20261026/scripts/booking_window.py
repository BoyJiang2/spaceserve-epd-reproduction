"""Require the current verified user booking, and leave two minutes for cleanup."""
import datetime
import json
from pathlib import Path
import time

ROOT = Path('/var/tmp/boyjiang-epd-revision-20261026')
START_MS = 1793019600000  # 2026-10-26 21:00 Asia/Shanghai
LATEST_END_MS = 1793062800000  # User's stated latest possible end: 2026-10-27 09:00
CLEANUP_SECONDS = 120


def validate(receipt, now_ms, fresh):
    booking = receipt['booking']
    verified = datetime.datetime.fromisoformat(receipt['verified_at_utc'])
    if verified.tzinfo is None:
        raise RuntimeError('booking verification time has no timezone')
    verified_ms = int(verified.timestamp() * 1000)
    if receipt['resource']['id'] != 'h20/qjh000' or not receipt['resource']['active']:
        raise RuntimeError('booking resource is wrong/inactive')
    if booking['resource_id'] != 'h20/qjh000' or booking['node'] != 'qjh000' or booking['user'] != 'boyjiang' or booking['kind'] != 'gpu':
        raise RuntimeError('booking owner/resource/lane mismatch')
    if booking['start_ms'] != START_MS or not START_MS < booking['end_ms'] <= LATEST_END_MS:
        raise RuntimeError('booking outside authorized overnight window')
    if not receipt.get('read_only') or verified_ms < booking['start_ms'] or verified_ms > now_ms + 2000:
        raise RuntimeError('booking proof must be refreshed after start, not future-dated')
    if fresh and now_ms - verified_ms > 300000:
        raise RuntimeError('booking proof older than five minutes; refresh before phase start')
    remaining = (booking['end_ms'] - now_ms) / 1000 - CLEANUP_SECONDS
    if now_ms < booking['start_ms'] or remaining <= 0:
        raise RuntimeError('outside booking or cleanup reserve')
    return remaining


def require(fresh=False):
    receipt = json.loads((ROOT / 'evidence/BOOKING_VERIFIED.json').read_text())
    return validate(receipt, int(time.time() * 1000), fresh)
