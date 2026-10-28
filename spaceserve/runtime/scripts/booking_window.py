"""Require the current verified user booking, and leave two minutes for cleanup."""
import datetime
import json
from pathlib import Path
import time

from runtime_config import context
CONFIG = context()
ROOT = CONFIG.run_root
SCOPE = CONFIG.config.get('booking') or {}
START_MS = SCOPE.get('start_ms')
LATEST_END_MS = SCOPE.get('end_ms')
AUTHORIZED_EXTENDED_END_MS = LATEST_END_MS  # No extension ticket in this window.
EXTENSION_ID = None
CLEANUP_SECONDS = 120
BOOKING_ID = SCOPE.get('id')
RESOURCE_ID = 'h20/' + CONFIG.config['host']


def validate(receipt, now_ms, fresh):
    if not BOOKING_ID or type(START_MS) is not int or type(LATEST_END_MS) is not int:
        raise RuntimeError('no exact booking configured; old windows are not a fallback')
    booking = receipt['booking']
    verified = datetime.datetime.fromisoformat(receipt['verified_at_utc'])
    if verified.tzinfo is None:
        raise RuntimeError('booking verification time has no timezone')
    verified_ms = int(verified.timestamp() * 1000)
    if receipt['resource']['id'] != RESOURCE_ID or not receipt['resource']['active']:
        raise RuntimeError('booking resource is wrong/inactive')
    if booking['resource_id'] != RESOURCE_ID or booking['node'] != CONFIG.config['host'] or booking['user'] != 'boyjiang' or booking['kind'] != 'gpu':
        raise RuntimeError('booking owner/resource/lane mismatch')
    if booking.get('id') != BOOKING_ID or booking['start_ms'] != START_MS or booking['end_ms'] != LATEST_END_MS:
        raise RuntimeError('booking differs from the exact authorized window')
    if receipt.get('read_only') is not True or verified_ms < booking['start_ms'] or verified_ms > now_ms + 2000:
        raise RuntimeError('booking proof must be refreshed after start, not future-dated')
    if fresh and now_ms - verified_ms > 300000:
        raise RuntimeError('booking proof older than five minutes; refresh before phase start')
    end_ms = booking['end_ms']
    extension = receipt.get('extension')
    if extension is not None:
        if EXTENSION_ID is None:
            raise RuntimeError('this window has no extension ticket')
        if (booking['end_ms'] != LATEST_END_MS or extension.get('id') != EXTENSION_ID
                or extension.get('resource_id') != RESOURCE_ID or extension.get('node') != CONFIG.config['host']
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
