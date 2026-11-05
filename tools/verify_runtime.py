"""Background-only handler/render validation. Sends NO operating-system input."""
import base64
import json
import time
from mcdk_rpc import McdkClient, ROOT

HEADER = "import mod.client.extraClientApi as api\nowner=api.GetSystem('bongocatmc','client')\n"


def execute(client, code):
    result=client.call('execute_code',{'code':HEADER+code,'is_client':True})
    if result.get('isError'):
        raise RuntimeError(result)
    for block in result.get('content',[]):
        text=block.get('text','')
        if 'Return value JSON: ' in text:
            return json.loads(text.split('Return value JSON: ',1)[1])
    raise RuntimeError(result)


def capture(client, name):
    result=client.call('capture_game_window',{})
    for block in result.get('content',[]):
        if block.get('type')=='image':
            path=ROOT/'diagnostics'/('hud_'+name+'.jpg')
            path.write_bytes(base64.b64decode(block['data']))
            return str(path)
    raise RuntimeError(result)


def main():
    c=McdkClient()
    state=execute(c,'_result=owner.hud.debug_state()')
    assert state['model']>=0 and not state['error'],state
    if not state['visible']:
        print('Skipped: HUD is hidden or a menu is open. No callbacks or native inputs sent.')
        return
    execute(c,"""owner._test_saved_inputs=owner.inputs
owner._test_saved_motion=owner.motion
owner._test_saved_sneak_query=owner.sneak_query
from bongocat_mod.client.input_state import InputState
class CatTestMotion(object):
    vector=(0.,0.)
    def GetInputVector(self): return self.vector
    def GetMolangValue(self, name): return 0
owner.inputs=InputState()
owner.motion=CatTestMotion()
owner.sneak_query=owner.motion
_result=True""")
    evidence={'mode':'background handler injection; no native mouse/keyboard input','cases':{}}
    try:
        cases=[
            ('w',"owner.key({'key':'87','isDown':'1'})",(True,False,False),'KeyW'),
            ('w_space',"owner.key({'key':'32','isDown':'1'})",(True,False,False),'Space'),
            ('release_space',"owner.key({'key':'32','isDown':'0'})",(True,False,False),'KeyW'),
            ('mouse_both',"owner.attack_down({})\nowner.use_down({})",(True,True,True),'KeyW'),
            ('release_all',"owner.key({'key':'87','isDown':'0'})\nowner.attack_up()\nowner.use_up()",(False,False,False),None),
            ('touch_move',"owner.motion.vector=(0.,1.)\nowner.move_down()",(True,False,False),'KeyW'),
            ('touch_jump',"owner.jump_down({'continueJump':True})\nowner.motion.vector=(0.,0.)\nowner.move_up()",(True,False,False),'Space'),
            ('touch_hold',"owner.jump_up()\nowner.hold({})",(False,True,False),None),
            ('touch_release',"owner.touch_up()",(False,False,False),None),
            ('menu_clear',"owner.move_down()\nowner.hold({})\nowner.menu_change({})",(False,False,False),None),
        ]
        for name,code,expected,art in cases:
            execute(c,code+'\n_result=True')
            time.sleep(.15)
            state=execute(c,'_result=owner.hud.debug_state()')
            actual=tuple(state['input'][k] for k in ('key','left','right'))
            assert actual==expected,(name,state)
            if art: assert state['input']['art']==art,(name,state)
            assert state['uniforms']['1'][3]==float(expected[0]),(name,state)
            assert state['uniforms']['2'][:2]==list(map(float,expected[1:])),(name,state)
            evidence['cases'][name]=state
            if name in ('w','mouse_both','release_all'):
                evidence['cases'][name]['screenshot']=capture(c,name)
        evidence['passed']=True
    finally:
        execute(c,'owner.inputs=owner._test_saved_inputs\nowner.motion=owner._test_saved_motion\nowner.sneak_query=owner._test_saved_sneak_query\ndel owner._test_saved_inputs\ndel owner._test_saved_motion\ndel owner._test_saved_sneak_query\n_result=True')
        (ROOT/'diagnostics/runtime_verification.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
    print('10 background handler/render cases passed; world and native inputs untouched.')


if __name__=='__main__':main()
