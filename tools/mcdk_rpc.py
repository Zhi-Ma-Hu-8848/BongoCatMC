"""Local MCP client for this project's explicitly configured MCDK port."""
import argparse
import base64
import json
from pathlib import Path
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


class McdkClient:
    def __init__(self):
        config = json.loads((ROOT/'.mcdev.json').read_text(encoding='utf8'))
        self.url = 'http://127.0.0.1:%d/mcp' % config['mcp_server_config']['server_port']
        self.session = None
        self.request('initialize', {'protocolVersion':'2024-11-05','capabilities':{},
                                   'clientInfo':{'name':'live2d-preview-debug','version':'0.1.0'}})
        self.request('notifications/initialized', notification=True)

    def request(self, method, params=None, notification=False):
        payload = {'jsonrpc':'2.0','method':method,'params':params or {}}
        if not notification:payload['id']='live2d-'+uuid.uuid4().hex
        headers = {'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
        if self.session:headers['Mcp-Session-Id']=self.session
        req = urllib.request.Request(self.url,json.dumps(payload).encode('utf8'),headers)
        with urllib.request.urlopen(req,timeout=20) as response:
            self.session=response.headers.get('Mcp-Session-Id',self.session)
            raw=response.read().decode('utf8')
        if not raw:return {}
        if raw.startswith(('event:','data:')):
            raw=next(line[5:].strip() for line in raw.splitlines() if line.startswith('data:'))
        value=json.loads(raw)
        if not notification and value.get('id')!=payload['id']:raise RuntimeError('Mismatched MCP response')
        if 'error' in value:raise RuntimeError(value['error'])
        return value.get('result',value)

    def call(self, name, args):
        return self.request('tools/call',{'name':name,'arguments':args})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('tool',nargs='?');p.add_argument('--args-file',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args();client=McdkClient()
    result=client.call(args.tool,json.loads(args.args_file.read_text(encoding='utf-8-sig')) if args.args_file else {}) if args.tool else client.request('tools/list')
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        for i,block in enumerate(result.get('content',[])):
            if block.get('type')=='image':
                dest=args.output.with_suffix('.%d.png'%i);dest.write_bytes(base64.b64decode(block['data']));block['data']=str(dest)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(str(args.output))
    else:print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':main()

