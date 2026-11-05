"""Read runtime health and save a screenshot of this project's MC window."""
import base64
import json
from pathlib import Path
from mcdk_rpc import McdkClient, ROOT


def call(client, name, args):
    result=client.call(name,args)
    for i,block in enumerate(result.get('content',[])):
        if block.get('type')=='image':
            dest=ROOT/'diagnostics'/('%s_%d.png'%(name,i))
            dest.write_bytes(base64.b64decode(block['data']))
            block['data']=str(dest)
    print(json.dumps(result,ensure_ascii=True))
    return result


if __name__=='__main__':
    c=McdkClient()
    call(c,'get_latest_error_logs',{'max_count':12})
    call(c,'execute_code',{'code':"import mod.client.extraClientApi as api\nowner=api.GetSystem('bongocatmc','client')\n_result=owner.hud.debug_state() if owner and owner.hud else str(owner)",'is_client':True})
    call(c,'mc_input',{'op':'/state'})
    call(c,'capture_game_window',{})
