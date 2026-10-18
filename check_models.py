"""Crate Digger prototype: verify the configured model IDs and structured-output support on OpenRouter.

Checks the configured IDs are in OpenRouter's model list and support structured outputs, then
(with --probe) makes one tiny structured call to each. The key is read from the macOS Keychain
(service "crate-digger-openrouter") or the OPENROUTER_API_KEY environment variable; it is never
written to disk or printed.
"""
import json, os, subprocess, sys, urllib.request, urllib.error

PRIMARY = os.environ.get('CD_PRIMARY_MODEL', 'openai/gpt-5.6-luna')
FALLBACK = os.environ.get('CD_FALLBACK_MODEL', 'anthropic/claude-haiku-5.5')
KEYCHAIN_SERVICE = 'crate-digger-openrouter'
URL = 'https://openrouter.ai/api/v1'
SCHEMA = {'type': 'object', 'properties': {'colour': {'type': 'string', 'enum': ['red', 'blue']}},
          'required': ['colour'], 'additionalProperties': False}

def api_key():
    k = os.environ.get('OPENROUTER_API_KEY')
    if k: return k
    try:
        return subprocess.run(['security', 'find-generic-password', '-s', KEYCHAIN_SERVICE, '-w'],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ''

def call(url, headers, body=None, timeout=20):
    req = urllib.request.Request(url, headers=headers, data=json.dumps(body).encode() if body else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {'error': e.read().decode()[:300]}
    except Exception as e:
        return 0, {'error': str(e)}

def headers():
    return {'Authorization': 'Bearer ' + api_key(), 'Content-Type': 'application/json', 'X-Title': 'Crate Digger'}

def chat(model, messages, schema, timeout=20):
    """One structured call. Routes only to providers that honour the schema and do not keep the data."""
    return call(URL + '/chat/completions', headers(), {
        'model': model, 'messages': messages,
        'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answer', 'strict': True, 'schema': schema}},
        'provider': {'require_parameters': True, 'data_collection': 'deny'}, 'usage': {'include': True}}, timeout)

if __name__ == '__main__':
    have_key = bool(api_key())
    for model in (PRIMARY, FALLBACK):
        st, d = call(URL + '/models/%s/endpoints' % model, {})
        if st != 200:
            print('%s: %s' % (model, 'NOT FOUND' if st == 404 else 'lookup failed (HTTP %s) %s' % (st, d.get('error')))); continue
        eps = d['data']['endpoints']
        structured = sorted({e['provider_name'] for e in eps if 'structured_outputs' in e.get('supported_parameters', [])})
        price = eps[0]['pricing'] if eps else {}
        print('%s: found, %d providers, structured outputs on %s; US$%.2f in / US$%.2f out per million tokens' % (
            model, len(eps), ', '.join(structured) or 'NONE', float(price.get('prompt', 0)) * 1e6, float(price.get('completion', 0)) * 1e6))
        if '--probe' in sys.argv:
            if not have_key: print('   probe skipped: no key in Keychain or OPENROUTER_API_KEY'); continue
            st, r = chat(model, [{'role': 'user', 'content': 'Pick red.'}], SCHEMA)
            print('   probe:', st, json.loads(r['choices'][0]['message']['content']) if st == 200 else r.get('error'))
