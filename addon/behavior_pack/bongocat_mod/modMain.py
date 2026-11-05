# -*- coding: utf-8 -*-
from mod.common.mod import Mod


@Mod.Binding(name='BongoCatMC', version='0.1.0')
class BongoCatMC(object):
    @Mod.InitClient()
    def init_client(self):
        import mod.client.extraClientApi as api
        api.RegisterSystem('bongocatmc', 'client', 'bongocat_mod.client.system.CatClient')
