"""Crate Digger prototype: verify the configured model IDs and structured-output support.

Asks each provider which models the key can use, checks the configured IDs are among them,
then (with --probe) makes one tiny structured call to each. Keys come from the environment
(OPENAI_API_KEY, ANTHROPIC_API_KEY); nothing is written to disk.
"""
import json, os, sys, urllib.request, urllib.error

PRIMARY = os.environ.get('CD_PRIMARY_MODEL', 'gpt-5.6-luna')
FALLBACK = os.environ.get('CD_FALLBACK_MODEL', 'claude-haiku-5.5')
SCHEMA = {'type': 'object', 'properties': {'colour': {'type': 'string', 'enum': ['red', 'blue']}},
          'required': ['colour'], 'additionalProperties': False}

def call(url, headers, body=None, timeout=20):
    req = urllib.request.Request(url, headers=headers, data=json.dumps(body).encode() if body else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {'error': e.read().decode()[:300]}
    except Exception as e:
        return 0, {'error': str(e)}

def openai_headers():
    return {'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'], 'Content-Type': 'application/json'}

def anthropic_headers():
    return {'x-api-key': os.environ['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'}

def list_models(name, url, headers, model):
    st, d = call(url, headers)
    if st != 200:
        print(f'{name}: model list failed (HTTP {st}) {d.get("error")}'); return False
    ids = sorted(m['id'] for m in d['data'])
    ok = model in ids
    print(f'{name}: {model!r} {"FOUND" if ok else "NOT FOUND"} among {len(ids)} models')
    if not ok:
        stem = model.split('-')[0]
        print('   similar:', ', '.join(i for i in ids if i.startswith(stem))[:400] or 'none')
    return ok

def probe_openai(model):
    st, d = call('https://api.openai.com/v1/chat/completions', openai_headers(), {
        'model': model, 'messages': [{'role': 'user', 'content': 'Pick red.'}],
        'response_format': {'type': 'json_schema', 'json_schema': {'name': 'p', 'strict': True, 'schema': SCHEMA}}})
    print('openai probe:', st, json.loads(d['choices'][0]['message']['content']) if st == 200 else d.get('error'))

def probe_anthropic(model):
    st, d = call('https://api.anthropic.com/v1/messages', anthropic_headers(), {
        'model': model, 'max_tokens': 100, 'messages': [{'role': 'user', 'content': 'Pick red.'}],
        'tools': [{'name': 'answer', 'description': 'Answer', 'input_schema': SCHEMA}],
        'tool_choice': {'type': 'tool', 'name': 'answer'}})
    print('anthropic probe:', st, next(b['input'] for b in d['content'] if b['type'] == 'tool_use') if st == 200 else d.get('error'))

if __name__ == '__main__':
    probe = '--probe' in sys.argv
    for name, var, url, hdr, model, fn in (
            ('openai', 'OPENAI_API_KEY', 'https://api.openai.com/v1/models', openai_headers, PRIMARY, probe_openai),
            ('anthropic', 'ANTHROPIC_API_KEY', 'https://api.anthropic.com/v1/models?limit=1000', anthropic_headers, FALLBACK, probe_anthropic)):
        if not os.environ.get(var):
            print(f'{name}: {var} not set, skipped'); continue
        if list_models(name, url, hdr(), model) and probe:
            fn(model)
