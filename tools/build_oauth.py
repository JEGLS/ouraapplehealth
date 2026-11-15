"""Build the OAuth versions of the Oura shortcuts.

Reads the signed personal-access-token shortcuts in the repo root, swaps the
API key Text block for an OAuth token refresh, writes an "Oura Setup"
shortcut, and saves unsigned files to oauth/unsigned/. Sign them on a Mac with
oauth/sign.sh before importing on iPhone.

Usage: python3 tools/build_oauth.py
"""
import os, sys, uuid, plistlib, copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzfse

OUT = os.path.join(ROOT, 'oauth', 'unsigned')
AUTH_FILE = 'oura_auth.json'
TOKEN_URL = 'https://api.ouraring.com/oauth/token'
REDIRECT = 'http://localhost'
SCOPES = 'personal daily heartrate spo2'
USER_AGENT = 'OuraAppleHealth/2.0'
OLD_KEY_UUID = 'C7EB608F-B986-4CE4-A8AE-DA5852851D6D'
OBJ = '￼'

SOURCES = [
    'Oura HRV', 'Oura HRV Continuous', 'Oura HRV Continuous Historical Data',
    'Oura RHR', 'Oura SPO2', 'Oura Temperature',
]


def uid():
    return str(uuid.uuid4()).upper()


def load_signed(path):
    data = open(path, 'rb').read()
    raw, _ = lzfse.decode(data, data.find(b'bvx2'))
    start = raw.find(b'bplist00')
    # Apple Archive entry: the DATA field just before the plist holds its size.
    size = int.from_bytes(raw[start - 2:start], 'little')
    return plistlib.loads(raw[start:start + size])


# ---- serialization helpers -------------------------------------------------

def out_ref(action_uuid, name):
    return {'OutputName': name, 'OutputUUID': action_uuid, 'Type': 'ActionOutput'}


def attachment(ref):
    return {'Value': ref, 'WFSerializationType': 'WFTextTokenAttachment'}


def tokens(*parts):
    """Build a WFTextTokenString from plain strings and output refs."""
    s, attach = '', {}
    for p in parts:
        if isinstance(p, str):
            s += p
        else:
            attach['{%d, 1}' % (len(s.encode('utf-16-le')) // 2)] = p
            s += OBJ
    val = {'string': s}
    if attach:
        val['attachmentsByRange'] = attach
    return {'Value': val, 'WFSerializationType': 'WFTextTokenString'}


def dict_field(items):
    return {'Value': {'WFDictionaryFieldValueItems': [
        {'WFItemType': 0, 'WFKey': tokens(k), 'WFValue': tokens(*v) if isinstance(v, tuple) else tokens(v)}
        for k, v in items]}, 'WFSerializationType': 'WFDictionaryFieldValue'}


def act(ident, **params):
    return {'WFWorkflowActionIdentifier': 'is.workflow.actions.' + ident,
            'WFWorkflowActionParameters': params}


def comment(text):
    return act('comment', WFCommentActionText=text)


def get_key(src_ref, key, name=None):
    u = uid()
    p = dict(UUID=u, WFDictionaryKey=key, WFGetDictionaryValueType='Value',
             WFInput=attachment(src_ref))
    if name:
        p['CustomOutputName'] = name
    return act('getvalueforkey', **p), out_ref(u, name or 'Dictionary Value')


def post_form(fields):
    u = uid()
    a = act('downloadurl', UUID=u, WFURL=tokens(TOKEN_URL), WFHTTPMethod='POST',
            WFHTTPBodyType='Form', WFFormValues=dict_field(fields), ShowHeaders=True,
            WFHTTPHeaders=dict_field([('User-Agent', USER_AGENT)]))
    return a, out_ref(u, 'Contents of URL')


def if_has_value(ref, group):
    return act('conditional', GroupingIdentifier=group, WFControlFlowMode=0, WFCondition=100,
               WFInput={'Type': 'Variable', 'Variable': attachment(ref)})


def otherwise(group):
    return act('conditional', GroupingIdentifier=group, WFControlFlowMode=1)


def end_if(group):
    return act('conditional', GroupingIdentifier=group, WFControlFlowMode=2, UUID=uid())


def get_file():
    u = uid()
    return act('documentpicker.open', UUID=u, WFGetFilePath=tokens(AUTH_FILE),
               WFFileErrorIfNotFound=True, WFShowFilePicker=False), out_ref(u, 'File')


def save_file(ref):
    return act('documentpicker.save', UUID=uid(), WFInput=attachment(ref),
               WFAskWhereToSave=False, WFSaveFileOverwrite=True,
               WFFileDestinationPath=tokens(AUTH_FILE))


def show(*parts):
    return act('showresult', Text=tokens(*parts))


# ---- token refresh block used by every data shortcut -----------------------

def token_block():
    acts = [comment('OAuth: refreshes the Oura access token using Shortcuts/' + AUTH_FILE
                    + ' in iCloud Drive. Run "Oura Setup" once before using this shortcut.')]
    a, f = get_file(); acts.append(a)
    du = uid(); acts.append(act('detect.dictionary', UUID=du, WFInput=attachment(f)))
    auth = out_ref(du, 'Dictionary')
    a, cid = get_key(auth, 'client_id', 'Client ID'); acts.append(a)
    a, csec = get_key(auth, 'client_secret', 'Client Secret'); acts.append(a)
    a, rtok = get_key(auth, 'refresh_token', 'Saved Refresh Token'); acts.append(a)
    a, resp = post_form([('grant_type', 'refresh_token'), ('refresh_token', (rtok,)),
                         ('client_id', (cid,)), ('client_secret', (csec,))]); acts.append(a)
    a, access = get_key(resp, 'access_token', 'Access Token'); acts.append(a)
    a, newr = get_key(resp, 'refresh_token', 'New Refresh Token'); acts.append(a)
    g = uid()
    acts.append(if_has_value(newr, g))
    su = uid()
    acts.append(act('setvalueforkey', UUID=su, WFDictionary=attachment(auth),
                    WFDictionaryKey='refresh_token', WFDictionaryValue=tokens(newr)))
    acts.append(save_file(out_ref(su, 'Dictionary')))
    acts.append(otherwise(g))
    acts.append(show('Oura token refresh failed. Run "Oura Setup" again.\n\nResponse from Oura:\n', resp))
    acts.append(act('exit'))
    acts.append(end_if(g))
    # Keep the original Text action UUID so the existing Authorization header still points at it.
    acts.append(act('gettext', UUID=OLD_KEY_UUID, WFTextActionText=tokens(access)))
    return acts


def convert(name):
    wf = load_signed(os.path.join(ROOT, name + '.shortcut'))
    actions = wf['WFWorkflowActions']
    assert actions[0]['WFWorkflowActionIdentifier'].endswith('comment')
    assert actions[1]['WFWorkflowActionParameters'].get('UUID') == OLD_KEY_UUID
    rest = actions[2:]
    for a in rest:
        if a['WFWorkflowActionIdentifier'].endswith('downloadurl'):
            items = a['WFWorkflowActionParameters']['WFHTTPHeaders']['Value']['WFDictionaryFieldValueItems']
            items.append({'WFItemType': 0, 'WFKey': tokens('User-Agent'), 'WFValue': tokens(USER_AGENT)})
    wf['WFWorkflowActions'] = token_block() + rest
    return wf


def setup_shortcut(template):
    acts = [comment('Run this once. It connects these shortcuts to your Oura account with OAuth.\n\n'
                    'Before running: on developer.ouraring.com, open your application and set its '
                    'Redirect URI to exactly ' + REDIRECT + '\n\n'
                    'Credentials are saved to iCloud Drive/Shortcuts/' + AUTH_FILE + '. '
                    'Run this again any time the other shortcuts report a token error.')]
    u = uid(); acts.append(act('ask', UUID=u, WFAskActionPrompt='Oura Client ID', WFInputType='Text'))
    cid = out_ref(u, 'Provided Input')
    u = uid(); acts.append(act('ask', UUID=u, WFAskActionPrompt='Oura Client Secret', WFInputType='Text'))
    csec = out_ref(u, 'Provided Input')
    u = uid()
    acts.append(act('url', UUID=u, **{'Show-WFURLActionURL': True}, WFURLActionURL=tokens(
        'https://cloud.ouraring.com/oauth/authorize?response_type=code&client_id=', cid,
        '&redirect_uri=' + REDIRECT.replace(':', '%3A').replace('/', '%2F')
        + '&scope=' + SCOPES.replace(' ', '%20') + '&state=shortcuts')))
    acts.append(act('openurl', UUID=uid(), WFInput=attachment(out_ref(u, 'URL')), **{'Show-WFInput': True}))
    u = uid()
    acts.append(act('ask', UUID=u, WFInputType='Text', WFAskActionPrompt=(
        'Sign in and tap Allow. Safari then shows a page that cannot load. '
        'Copy the full address from the address bar (it starts with http://localhost/?code=) and paste it here.')))
    pasted = out_ref(u, 'Provided Input')
    u = uid()
    acts.append(act('text.match', UUID=u, WFMatchTextCaseSensitive=False,
                    WFMatchTextPattern=r'(?<=code=)[^&#\s]+|^[^=&:/\s]+$', text=tokens(pasted)))
    u2 = uid()
    acts.append(act('getitemfromlist', UUID=u2, WFItemSpecifier='First Item',
                    WFInput=attachment(out_ref(u, 'Matches'))))
    code = out_ref(u2, 'Item from List')
    a, resp = post_form([('grant_type', 'authorization_code'), ('code', (code,)),
                         ('redirect_uri', REDIRECT), ('client_id', (cid,)), ('client_secret', (csec,))])
    acts.append(a)
    a, rtok = get_key(resp, 'refresh_token', 'Refresh Token'); acts.append(a)
    g = uid()
    acts.append(if_has_value(rtok, g))
    du = uid()
    acts.append(act('dictionary', UUID=du, WFItems=dict_field([
        ('client_id', (cid,)), ('client_secret', (csec,)), ('refresh_token', (rtok,))])))
    acts.append(save_file(out_ref(du, 'Dictionary')))
    acts.append(show('Oura is connected. Your other Oura shortcuts will now refresh their access automatically.'))
    acts.append(otherwise(g))
    acts.append(show('Oura setup failed. Check the client ID, client secret and redirect URI, then run this again. '
                     'The code from Safari expires after a few minutes.\n\nResponse from Oura:\n', resp))
    acts.append(end_if(g))
    wf = copy.deepcopy(template)
    wf['WFWorkflowActions'] = acts
    wf['WFWorkflowTypes'] = []
    wf['WFWorkflowIcon'] = {'WFWorkflowIconGlyphNumber': 59511, 'WFWorkflowIconStartColor': 4282601983}
    return wf


def check(name, wf):
    """Every referenced action output must exist earlier; If blocks must balance."""
    seen, stack = set(), []

    def refs(o):
        if isinstance(o, dict):
            if o.get('Type') == 'ActionOutput':
                yield o['OutputUUID']
            for v in o.values():
                yield from refs(v)
        elif isinstance(o, list):
            for v in o:
                yield from refs(v)

    for a in wf['WFWorkflowActions']:
        p = a['WFWorkflowActionParameters']
        for r in refs(p):
            assert r in seen, (name, a['WFWorkflowActionIdentifier'], r)
        if 'GroupingIdentifier' in p:
            mode = p['WFControlFlowMode']
            if mode == 0:
                stack.append(p['GroupingIdentifier'])
            else:
                assert stack and stack[-1] == p['GroupingIdentifier'], name
                if mode == 2:
                    stack.pop()
        if 'UUID' in p:
            seen.add(p['UUID'])
    assert not stack, name


def main():
    os.makedirs(OUT, exist_ok=True)
    template = None
    for name in SOURCES:
        wf = convert(name)
        template = template or wf
        check(name, wf)
        with open(os.path.join(OUT, name + '.shortcut'), 'wb') as f:
            plistlib.dump(wf, f, fmt=plistlib.FMT_BINARY)
        print('built', name, len(wf['WFWorkflowActions']), 'actions')
    wf = setup_shortcut(template)
    check('Oura Setup', wf)
    with open(os.path.join(OUT, 'Oura Setup.shortcut'), 'wb') as f:
        plistlib.dump(wf, f, fmt=plistlib.FMT_BINARY)
    print('built Oura Setup', len(wf['WFWorkflowActions']), 'actions')


if __name__ == '__main__':
    main()
