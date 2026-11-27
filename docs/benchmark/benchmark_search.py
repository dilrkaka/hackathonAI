#!/usr/bin/env python3
"""Compare baseline and smart search against a CSV gold set."""
import argparse
import json
import shutil
import time
from pathlib import Path

import pandas as pd
import requests


def as_ids(value):
    return {x.strip() for x in str(value or '').split(';') if x.strip()}


def product_id(p):
    return str(p.get('id', p.get('product_id', '')))


def relevant(p, row, strict=False):
    ids = as_ids(row.get('expected_product_ids', ''))
    cats = as_ids(row.get('expected_category_ids', ''))
    match_id = product_id(p) in ids
    match_cat = str(p.get('category_id', p.get('categoryId', ''))) in cats
    if strict and ids:
        return match_id
    return match_id or match_cat


def summarize(g):
    ok = g[g.status == 'ok']
    result = dict(n_queries=len(g), successful=len(ok), errors=len(g)-len(ok),
                  error_rate=(len(g)-len(ok))/len(g))
    for col, name in [('precision_at_4','precision_at_4_mean'),
                      ('hit_rate_at_4','hit_rate_at_4'),
                      ('strict_precision_at_4','strict_precision_at_4_mean'),
                      ('strict_hit_rate_at_4','strict_hit_rate_at_4'),
                      ('empty_result','empty_rate'), ('at_least_4','rate_at_least_4')]:
        result[name] = ok[col].mean()
    # Legacy metrics treat errors as zero hits / empty responses.
    for col, name in [('precision_at_4','legacy_precision_at_4_mean'),
                      ('hit_rate_at_4','legacy_hit_rate_at_4'),
                      ('at_least_4','legacy_rate_at_least_4')]:
        result[name] = g[col].fillna(0).mean()
    result['legacy_empty_rate'] = g.empty_result.fillna(1).mean()
    for col, prefix in [('latency_ms','latency'), ('server_processing_time_ms','server_processing_time')]:
        values = pd.to_numeric(ok[col], errors='coerce').dropna()
        result[f'median_{prefix}_ms'] = values.median()
        result[f'p95_{prefix}_ms'] = values.quantile(.95)
        result[f'n_{prefix}_samples'] = len(values)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-url', default='https://hackathon-test-production-db3ed6b7.up.railway.app')
    ap.add_argument('--csv', default='softline_search_benchmark_60.csv')
    ap.add_argument('--limit', type=int, default=4, choices=range(4,21))
    ap.add_argument('--timeout', type=float, default=30)
    ap.add_argument('--out', default='benchmark_results')
    ap.add_argument('--commit', default='0174ad1', help='Expected deployed commit; verify in Railway')
    ap.add_argument('--warmup', type=int, default=3)
    ap.add_argument('--previous', help='Previous summary.csv for legacy metric comparison')
    args = ap.parse_args()
    if args.warmup < 1 or args.timeout <= 0:
        ap.error('warmup and timeout must be positive')
    base = args.base_url.rstrip('/')
    tests = pd.read_csv(args.csv, keep_default_na=False, dtype=str)
    required = {'query','query_type','expected_product_ids','expected_category_ids'}
    if missing := required - set(tests.columns):
        ap.error(f'Missing CSV columns: {sorted(missing)}')
    if tests.empty:
        ap.error('Empty benchmark CSV')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out/'gold_input.csv'
    if Path(args.csv).resolve() != target.resolve():
        shutil.copyfile(args.csv, target)
    metadata = dict(expected_commit=args.commit, commit_verified=False, base_url=base,
                    n_queries=len(tests), limit=args.limit, metric_k=4,
                    warmup_per_mode=args.warmup, log=False,
                    mode_order='alternating', relevance='ID OR category; strict: ID if supplied, else category',
                    primary_metrics='successful responses only; legacy includes errors as misses')
    (out/'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = []
    with requests.Session() as session:
        def request(mode, query):
            return session.post(f'{base}/api/search/{mode}',
                                json={'query':query,'limit':args.limit,'log':False}, timeout=args.timeout)
        # Warm up both modes; abort rather than measure an unhealthy service.
        for i in range(args.warmup):
            for mode in ('baseline','smart'):
                response = request(mode, tests.iloc[i % len(tests)]['query'])
                response.raise_for_status()
                if not isinstance(response.json().get('products'), list):
                    raise ValueError(f'Invalid warmup response: {mode}')
        with (out/'raw_responses.jsonl').open('w', encoding='utf-8') as raw:
            for i, r in tests.iterrows():
                modes = ('baseline','smart') if i % 2 == 0 else ('smart','baseline')
                for mode in modes:
                    resp = None
                    elapsed = None
                    body = None
                    payload = {'query':r['query'],'limit':args.limit,'log':False}
                    row = dict(query=r['query'], query_type=r['query_type'], mode=mode)
                    started = time.perf_counter()
                    try:
                        resp = request(mode, r['query'])
                        elapsed = (time.perf_counter()-started)*1000
                        resp.raise_for_status()
                        body = resp.json()
                        products = body.get('products')
                        if not isinstance(products, list):
                            raise ValueError('Missing or invalid products list')
                        hits = products[:4]
                        rel = [p for p in hits if relevant(p,r)]
                        strict = [p for p in hits if relevant(p,r,strict=True)]
                        row.update(status='ok', http_status=resp.status_code,
                                   returned_top4=len(hits), relevant_top4=len(rel),
                                   precision_at_4=len(rel)/4, hit_rate_at_4=int(bool(rel)),
                                   strict_precision_at_4=len(strict)/4, strict_hit_rate_at_4=int(bool(strict)),
                                   empty=int(not hits), empty_result=int(not hits), at_least_4=int(len(hits)>=4),
                                   latency_ms=elapsed, server_processing_time_ms=body.get('processing_time_ms'),
                                   returned_ids=';'.join(map(product_id,hits)), relevant_ids=';'.join(map(product_id,rel)),
                                   strict_relevant_ids=';'.join(map(product_id,strict)), error='')
                    except Exception as e:
                        if elapsed is None:
                            elapsed = (time.perf_counter()-started)*1000
                        row.update(status='error', http_status=resp.status_code if resp is not None else None,
                                   returned_top4=None, relevant_top4=None, precision_at_4=None, hit_rate_at_4=None,
                                   strict_precision_at_4=None, strict_hit_rate_at_4=None, empty=None, empty_result=None,
                                   at_least_4=None, latency_ms=elapsed, server_processing_time_ms=None,
                                   returned_ids='', relevant_ids='', strict_relevant_ids='', error=str(e))
                    rows.append(row)
                    raw.write(json.dumps(dict(query=r['query'], mode=mode, request=payload, response=body,
                                              status=row['status'], http_status=row['http_status'], error=row['error'],
                                              response_text=resp.text if resp is not None and row['status']=='error' else None),
                                         ensure_ascii=False)+'\n')
                print(f'{i+1}/{len(tests)}: {r["query"]}', flush=True)
    result = pd.DataFrame(rows)
    result.to_csv(out/'per_query.csv', index=False, encoding='utf-8-sig')
    summary = pd.DataFrame([dict(mode=m, **summarize(g)) for m,g in result.groupby('mode')])
    summary.to_csv(out/'summary.csv', index=False, encoding='utf-8-sig')
    by_type = pd.DataFrame([dict(mode=m, query_type=t, **summarize(g))
                            for (m,t),g in result.groupby(['mode','query_type'])])
    by_type.to_csv(out/'by_query_type.csv', index=False, encoding='utf-8-sig')
    if args.previous:
        prev = pd.read_csv(args.previous)
        comparison = []
        for _, current in summary.iterrows():
            old = prev[prev['mode']==current['mode']]
            if old.empty:
                continue
            for metric in ('precision_at_4_mean','hit_rate_at_4','empty_rate','rate_at_least_4',
                           'median_latency_ms','p95_latency_ms'):
                if metric not in old.columns:
                    continue
                before = float(old.iloc[0][metric])
                after = current.get('legacy_'+metric, current[metric])
                comparison.append(dict(mode=current['mode'], metric=metric, before=before,
                                       after=after, delta=after-before,
                                       note='Warmup/order differ; latency comparison exploratory' if 'latency' in metric else 'Legacy relevance and error policy'))
        pd.DataFrame(comparison).to_csv(out/'comparison.csv', index=False, encoding='utf-8-sig')
    print(summary.to_string(index=False))
    print(f'\nSaved: {out.resolve()}')


if __name__ == '__main__':
    main()
