from flask import Blueprint, jsonify
from typing import List, Dict
from collections import deque

# In-memory ring buffer for logs
_LOGS: deque = deque(maxlen=200)


def add_log(entry: Dict):
    _LOGS.appendleft(entry)


logs_bp = Blueprint('logs', __name__, url_prefix='/api')


@logs_bp.get('/logs')
def get_logs():
    return jsonify(list(_LOGS))
