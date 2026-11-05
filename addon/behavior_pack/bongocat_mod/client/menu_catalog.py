# -*- coding: utf-8 -*-
"""Shared default-model menu entries, consumed by UI build and client."""
ENTRIES = {
    'motions': [('stop',u'停止所有动作'),('flash',u'闪电'),('wave',u'挥手')],
    'expressions': [('stop',u'停止所有表情'),('default',u'默认'),('glasses',u'墨镜'),('halo',u'光环')]
}
MODEL_ENTRIES = {'default':dict(ENTRIES), 'deepseek':{
    'motions':[('stop',u'停止所有动作'),('Surprised',u'惊讶'),('Hello',u'打招呼'),('Sweat',u'流汗'),('Heart',u'爱心')],
    'expressions':[('stop',u'停止所有表情'),('Bowl',u'碗'),('Glasses',u'眼镜'),('StickyNotes',u'便利贴'),('Egg',u'彩蛋')]
}}
for group in ('motions','expressions'):
    ENTRIES[group] = ENTRIES[group]+MODEL_ENTRIES['deepseek'][group][1:]
ENTRIES['models'] = [('default',u'默认小猫'),('deepseek',u'DeepSeek')]

def entries_for(model, group):
    return ENTRIES['models'] if group=='models' else MODEL_ENTRIES.get(model,MODEL_ENTRIES['default'])[group]
ROW_HEIGHT = 30
LIST_WIDTH = 78
MAX_VISIBLE_ROWS = 3.5
