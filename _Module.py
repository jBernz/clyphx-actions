from _EbiagiComponent import EbiagiComponent
from _naming_conventions import *
from _Instrument import Instrument
from _Loop import Loop
from _Snap import Snap

class Module(EbiagiComponent):

    def __init__(self, track, Set, m=0, a=0):
        super(Module, self).__init__()
        self._track = track
        self._set = Set
        self.instruments = []
        self.loops = {}

        self.short_name = get_short_name(track.name.split('.')[0])

        self._snap_data = self._track.get_data('snaps', False) or [[],[],[],[],[],[]]
        self.snaps = []

        self.log('Initializing Module %s...' % self.short_name)

        i = list(self._song.tracks).index(track) + 1
        while not is_module(self._song.tracks[i].name) and self._song.tracks[i].is_grouped:

            #Add Instruments
            if is_instrument(self._song.tracks[i].name):
                instr = Instrument(self._song.tracks[i], Set)
                if instr.has_midi_input():
                    instr.set_midi_router(Set.midi_routers[m])
                    m += 1
                if instr.has_audio_input():
                    instr.set_audio_router(Set.audio_routers[a])
                    a += 1
                self.instruments.append(instr)

            i += 1

        for scene in self._song.scenes:
            if is_loop(scene.name):
                loop = Loop(track, scene, Set, self.instruments)
                self.loops[loop.short_name] = loop

        for snap in self._snap_data:
            self.snaps.append(Snap(snap, self, Set))

                
    def activate(self):
        self.log('Activating %s...' % self.short_name)
        for instrument in self.instruments:
            instrument.activate()
        self._track.fold_state = 0
        self._track.mute = 0

    def deactivate(self):
        self.log('Deactivating %s...' % self.short_name)
        for instrument in self.instruments:
            instrument.deactivate()
        self._track.fold_state = 1
        self._track.mute = 1

    def assign_snap(self, index, param, track):
        for instrument in self.instruments:
            if instrument._track == track:
                if not self.snaps[index].has_param(param):
                    self.snaps[index].create_param(instrument, param)
                    self.message('Added param %s to snap %s at %s' % (param.name, str(index+1), str(param.value)))
                else:
                    self.snaps[index].remove_param(param)
                    self.message('Removed param %s from snap %s' % (param.name, str(index+1)))
                self._save_snaps()

    def clear_snap(self, index):
        self.snaps[index] = Snap([], self, self._set)
        self._save_snaps()
        self.message('Removed all params from snap %s' % str(index+1))

    def _save_snaps(self):
        data = []
        for snap in self.snaps:
            data.append(snap.get_data())
        self._track.set_data('snaps', data)
        self._snap_data = data
        self.log('saved snaps')
        self.log(self._track.get_data('snaps', False))
