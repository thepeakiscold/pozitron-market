#!/usr/bin/env python3
"""Workspace product review queue. Uses the same SQLite state as the admin checkbox."""
import argparse
import contextlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import database
import product_quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    queue = sub.add_parser('next', help='Print unchecked products and their content fingerprints')
    queue.add_argument('--limit', type=int, default=1)
    queue.add_argument('--include-issues', action='store_true')
    sub.add_parser('stats')
    record = sub.add_parser('record', help='Record one JSON review report')
    record.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    with contextlib.redirect_stdout(sys.stderr):
        database.init_db()
    conn = database.get_db()
    try:
        if args.command in ('next', 'stats'):
            products = [dict(row) for row in conn.execute('SELECT * FROM products ORDER BY sku, id')]
            states = product_quality.states(conn, products)
            if args.command == 'stats':
                result = {status: sum(state['quality_status'] == status for state in states.values())
                          for status in ('pending', 'checked', 'issues')}
                result['total'] = len(products)
            else:
                if not 1 <= args.limit <= 100:
                    parser.error('--limit 1 ile 100 arasında olmalıdır.')
                result = []
                for product in products:
                    state = states[product['id']]
                    if state['quality_status'] != 'pending' and not (args.include_issues and state['quality_status'] == 'issues'):
                        continue
                    result.append({**product_quality.snapshot(product), **state})
                    if len(result) >= args.limit:
                        break
        else:
            report = json.loads(args.report.read_text())
            required = ('product_id', 'status', 'content_hash', 'reviewer', 'notes', 'sources')
            if any(key not in report for key in required):
                raise ValueError('Raporda gerekli alanlar eksik: ' + ', '.join(required))
            if not isinstance(report['content_hash'], str) or len(report['content_hash']) != 64:
                raise ValueError('Geçerli content_hash gereklidir.')
            if not isinstance(report['reviewer'], str) or not report['reviewer'].strip():
                raise ValueError('İnceleyen bilgisi gereklidir.')
            if report['status'] == 'checked' and (not report['sources'] or not report['notes'].strip()):
                raise ValueError('LLM onayı için kaynak ve inceleme notu gereklidir.')
            result = product_quality.record_check(conn, report['product_id'], report['status'],
                reviewer=report['reviewer'], notes=report['notes'], sources=report['sources'],
                expected_hash=report['content_hash'])
            conn.commit()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, LookupError, OSError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
