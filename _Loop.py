from _EbiagiComponent import EbiagiComponent
from _naming_conventions import *
from _utils import is_empty_midi_clip

class Loop(EbiagiComponent):

    def __init__(self, track, scene, Set, instruments):
        super(Loop, self).__init__()
        self._track = track
        self._scene = scene
        self._set = Set

        s = list(self._song.scenes).index(scene)
        self._main_clip_slot = track.clip_slots[s]
        self._clip_slots = []

        self.short_name = get_short_name(scene.name)

        self.log('Initializing Loop %s %s...' % (get_short_name(track.name), self.short_name))

        i = list(self._song.tracks).index(track) + 1
        while not is_module(self._song.tracks[i].name) and self._song.tracks[i].is_grouped:
            instr = None
            for instrument in instruments:
                if instrument.has_track(self._song.tracks[i]):
                    instr = instrument
            if instr:
                clip_slot = ClipSlot(self._song.tracks[i].clip_slots[s], self._song.tracks[i], instr, Set)
                self._clip_slots.append(clip_slot)
            i += 1

    def select(self):
        if self.is_recording():
            self._finish_record()
        elif self.is_playing():
            #self.display_first_clip()
            for clip_slot in self._clip_slots:
                clip_slot.run_select_commands()
            return
        else:
            #self._main_clip_slot.fire()
            for clip_slot in self._clip_slots:
                clip_slot.fire()
                clip_slot.run_select_commands()

    def deselect(self):
        for clip_slot in self._clip_slots:
            clip_slot.run_deselect_commands()

    def stop(self):
        if self.is_recording():
            self._finish_record()
        for clip_slot in self._clip_slots:
            if not clip_slot.is_group_clip():
                clip_slot.stop()

    def clear(self):
        for clip_slot in self._clip_slots:
            if clip_slot.is_clearable():
                clip_slot.clear()

    def _finish_record(self):
        has_clip = False
        for clip_slot in self._clip_slots:
            if clip_slot.is_recording():
                if clip_slot.finish_record():
                    has_clip = True
        if not has_clip:
            self.clear()

    def quantize(self):
        for clip_slot in self._clip_slots:
            clip_slot.quantize()

    def can_record(self):
        will_record = False
        for clip_slot in self._clip_slots:
            if clip_slot.will_record_on_start():
                will_record = True
        return will_record or self._main_clip_slot.is_recording
    
    def color(self):
        if self.has_clips():
            return self._main_clip_slot.color_index or 55
        else:
            return 'none'

    def is_playing(self):
        return self._main_clip_slot.is_playing

    def is_recording(self):
        return self._main_clip_slot.is_recording

    def has_clips(self):
        for clip_slot in self._clip_slots:
            if clip_slot.has_clip():
                return True
        return False

    def display_first_clip(self):
        for clip_slot in self._clip_slots:
            if clip_slot.has_clip:
                self.module.set.base.song().view.detail_clip = clip_slot.clip
                self.module.set.base.canonical_parent.application().view.show_view('Detail/Clip')
                return


#Wrapper for clip_slot to add its track
class ClipSlot(EbiagiComponent):

    def __init__(self, slot, track, instrument=None, Set=None):
        super(ClipSlot, self).__init__()
        self._slot = slot
        self._track = track
        self._instrument = instrument
        self._set = Set
        self._held = False
        if self._slot.has_clip:
            self.name = parse_clip_name(self._slot.clip.name)
            self._clip_commands = parse_clip_commands(self._slot.clip.name) or []

    #(because clip_slot.will_record_on_start does not work)
    def will_record_on_start(self):
        return not self._slot.has_clip and self._slot.has_stop_button and self._track.can_be_armed and self._track.arm

    def fire(self):
        if self.will_record_on_start() and not self._instrument.is_selected():
            return
        else:
            self._slot.fire()

    def stop(self):
        self._slot.stop()

    def is_clearable(self):
        return self._slot.has_clip and 'CAN_CLEAR' in self._slot.clip.name or self._slot.is_recording

    def is_recording(self):
        return self._slot.is_recording

    def finish_record(self):
        self._slot.clip.name = 'CAN_CLEAR'
        if self._slot.clip.is_midi_clip:
            if is_empty_midi_clip(self._slot.clip):
                self.deactivate_clip()
                return False
        if self._slot.clip.is_audio_clip:
            if not self._instrument.audio_in_armed():
                self.deactivate_clip()
                return False
        self._slot.fire()
        return True

    def is_group_clip(self):
        return self._slot.controls_other_clips

    def has_clip(self):
        return self._slot.has_clip

    def deactivate_clip(self):
        self._slot.clip.muted = 1
        self._slot.has_stop_button = 0

    def clear(self):
        if self._slot.has_clip:
            self._slot.delete_clip()
            self._slot.has_stop_button = 1

    def quantize(self):
        if self._slot.has_clip and self._slot.clip.is_midi_clip:
            self._slot.clip.quantize(5, 1.0)

    def run_select_commands(self):
        if self._slot.has_clip:

            self._held = True

            for command in self._clip_commands:

                if 'SELECT' in command:
                    self._set.select_instrument(None, self._instrument)
                    self._set.deselect_instrument(None, self._instrument)

                if 'SNAP' in command:
                    index = int(parse_clip_command_param(command))
                    self.log(index)
                    self._set.snap_control.select_snap(self._set.active_module.snaps[index])
                    self._set.snap_control.ramp(0)

                if 'PLAY' in command:
                    clip_name_to_play = parse_clip_command_param(command)
                    self.log(clip_name_to_play)
                    for clip_slot in self._track.clip_slots:
                        if clip_slot.has_clip:
                            self.log(parse_clip_name(clip_slot.clip.name))
                            if parse_clip_name(clip_slot.clip.name) == clip_name_to_play:
                                clip_slot.fire()

                if 'STOP' in command:
                    self._track.stop_all_clips()

    
    def run_deselect_commands(self):
        if self._slot.has_clip:

            for command in self._clip_commands:

                if 'HOLD' in command and self._held:
                    can_stop = True
                    for clip_slot in self._track.clip_slots:
                        if (clip_slot.is_playing or clip_slot.is_triggered) and clip_slot.clip != self._slot.clip:
                            can_stop = False
                    if can_stop:
                        list(self._track.clip_slots)[self._set.get_scene_index('STOPCLIP')].fire()

            self._held = False


