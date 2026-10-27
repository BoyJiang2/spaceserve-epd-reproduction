"""Require the current verified user booking, and leave two minutes for cleanup."""
import datetime
import json
from pathlib import Path
import time

ROOT = Path('/var/tmp/boyjiang-spaceserve-window-20261027-1300')
START_MS = 1793077200000  # 2026-10-27 13:00 Asia/Shanghai
LATEST_END_MS = 1793091600000  # User's stated latest possible end: 2026-10-27 17:00
AUTHORIZED_EXTENDED_END_MS = 1793095200000  # User explicitly authorized 18:00, not the ticket's 19:00.
EXTENSION_ID = 'bk-20261027T0532-efb16fde'
CLEANUP_SECONDS = 120
BOOKING_ID = 'bk-20261027T0137-bcf3dd23'


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
    if booking.get('id') != BOOKING_ID or booking['start_ms'] != START_MS or not START_MS < booking['end_ms'] <= LATEST_END_MS:
        raise RuntimeError('booking outside authorized afternoon window')
    if not receipt.get('read_only') or verified_ms < booking['start_ms'] or verified_ms > now_ms + 2000:
        raise RuntimeError('booking proof must be refreshed after start, not future-dated')
    if fresh and now_ms - verified_ms > 300000:
        raise RuntimeError('booking proof older than five minutes; refresh before phase start')
    end_ms = booking['end_ms']
    extension = receipt.get('extension')
    if extension is not None:
        if (booking['end_ms'] != LATEST_END_MS or extension.get('id') != EXTENSION_ID
                or extension.get('resource_id') != 'h20/qjh000' or extension.get('node') != 'qjh000'
                or extension.get('user') != 'boyjiang' or extension.get('kind') != 'gpu'
                or extension.get('start_ms') != LATEST_END_MS
                or extension.get('end_ms', 0) < AUTHORIZED_EXTENDED_END_MS):
            raise RuntimeError('extension is not the actual contiguous owned GPU booking')
        end_ms = AUTHORIZED_EXTENDED_END_MS
    remaining = (end_ms - now_ms) / 1000 - CLEANUP_SECONDS
    if now_ms < booking['start_ms'] or remaining <= 0:
        raise RuntimeError('outside booking or cleanup reserve')
    return remaining


def require(fresh=False):
    receipt = json.loads((ROOT / 'evidence/BOOKING_VERIFIED.json').read_text())
    return validate(receipt, int(time.time() * 1000), fresh)
