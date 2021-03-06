from _EbiagiComponent import EbiagiComponent
from _naming_conventions import *
from _Module import Module
from _Input import Input
from _Router import Router
from _Instrument import Instrument
from _SnapControl import SnapControl

class Set(EbiagiComponent):

    def __init__(self):
        super(Set, self).__init__()

        self.loading = True
        self.log('Loading Set...')

        self.inputs = {}

        self.midi_routers = []
        self.audio_routers = []
        
        self.snap_control = None

        self.modules = []
        self.active_module = None

        self.global_instruments = []
        self.global_loop = None

        self.held_instruments = set([])

        m = 0
        a = 0
        for track in self._song.tracks:

            #Add inputs
            if is_input(track.name):
                ipt = Input(track, self)
                self.inputs[ipt.short_name] = ipt

            #Add midi routers       
            if is_midi_router(track.name):
                self.midi_routers.append(Router(track, self)) 
            
            #Add audio routers       
            if is_audio_router(track.name):
                self.audio_routers.append(Router(track, self))

        for track in self._song.tracks:

            #Add Global Instrument
            if is_global_instrument(track.name):
                instr = Instrument(track, self)
                if instr.has_midi_input():
                    instr.set_midi_router(self.midi_routers[m])
                    m += 1
                if instr.has_audio_input():
                    instr.set_audio_router(self.audio_routers[a])
                    a += 1
                self.global_instruments.append(instr)

            #Add Snap Control
            if is_snap_control(track.name):
                sc = SnapControl(track, self)
                sc.set_midi_router(self.midi_routers[m])
                m += 1
                self.snap_control = sc

            #Add global loop
            if is_global_loop_track(track.name):
                self.global_loop = track.clip_slots[0]

        for track in self._song.tracks:

            #Add modules
            if is_module(track.name):
                module = Module(track, self, m, a)
                self.modules.append(module)
                module.deactivate()

        if len(self.modules):
            self.activate_module(0)
            self.loading = False
            self.message('Loaded Ebiagi Set')

    def activate_module(self, index):
        if self.modules[index]:
            if self.modules[index] != self.active_module:

                if self.active_module:
                    self.active_module.deactivate()

                for router in self.midi_routers and self.audio_routers:
                    router.set_instrument(None)

                self.modules[index].activate()
                self.active_module = self.modules[index]
            else:
                self.message('Module already active')
        else:
            self.log('Module index out of bounds')

    def toggle_input(self, key):
        self.inputs[key].toggle()

    def select_instrument(self, index, instrument=None):
        if not instrument:
            instrument = self.active_module.instruments[index]
        self.log(instrument.short_name)
        self.held_instruments.add(instrument)
        instrument.select()
        self._update_routers()

    def deselect_instrument(self, index, instrument=None):
        if not instrument:
            instrument = self.active_module.instruments[index]       
        if instrument in self.held_instruments: 
            self.held_instruments.remove(instrument)
        instrument.deselect()
        self._update_routers()

    def stop_instrument(self, index, instrument=None):
        if not instrument:
            instrument = self.active_module.instruments[index]       
        instrument.stop()

    def select_loop(self, key):
        self.active_module.loops[key].select()

    def deselect_loop(self, key):
        self.active_module.loops[key].deselect()

    def stop_loop(self, key):
        self.active_module.loops[key].stop()

    def stop_all_loops(self):
        for loop in self.active_module.loops.values():
            loop.stop()

    def clear_loop(self, key):
        self.active_module.loops[key].clear()

    def quantize_loop(self, key):
        self.active_module.loops[key].quantize()

    def mute_all_loops(self):
        instrs = self.held_instruments if len(self.held_instruments) > 0 else self.active_module.instruments
        for instr in instrs:
            instr.mute_loops()

    def unmute_all_loops(self):
        for instr in self.active_module.instruments:
            instr.unmute_loops()

    def select_snap(self, index):
        self.snap_control.select_snap(self.active_module.snaps[index])
        self.select_instrument(None, self.snap_control)

    def deselect_snap(self, index):       
        self.deselect_instrument(None, self.snap_control)

    def assign_snap(self, index):
        param = self._song.view.selected_parameter
        track = self._song.view.selected_track
        self.active_module.assign_snap(index, param, track)

    def clear_snap(self, index):
        self.active_module.clear_snap(index)

    def recall_snap(self, beats):
        self.snap_control.ramp(beats)

    def select_global_instrument(self, index):
        self.select_instrument(None, self.global_instruments[index])

    def deselect_global_instrument(self, index):
        self.deselect_instrument(None, self.global_instruments[index])

    def select_global_loop(self):
        if self.global_loop.is_playing:
            self.setCrossfadeA()
        self.global_loop.fire()

    def stop_global_loop(self):
        self.global_loop.stop()

    def clear_global_loop(self):
        self.global_loop.delete_clip()
        self.setCrossfadeB()

    def setCrossfadeA(self):
        self._song.master_track.mixer_device.crossfader.value = -1.0

    def setCrossfadeB(self):
        self._song.master_track.mixer_device.crossfader.value = 1.0

    def toggle_metronome(self):
        self._song.metronome = not self._song.metronome

    #TODO: Performance can be improved by mapping names
    def get_scene_index(self, name):
        i = 0
        for scene in self._song.scenes:
            if name == scene.name:
                return i
            i += 1

    def _update_routers(self):
        for ipt in self.inputs.values():
            if not ipt.empty():
                if ipt.has_midi_input:
                    for router in self.midi_routers:
                        router.update_input(ipt)
                if ipt.has_audio_input:
                    for router in self.audio_routers:
                        router.update_input(ipt)
